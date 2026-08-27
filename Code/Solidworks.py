"""
V5 유로+방열핀 9변수 — SolidWorks COM 자동화 (글로벌 변수 제어 + STEP 저장)

V4(Code3) 대비 변경점
  - 글로벌 변수 8개 → 11개 (자유변수 10 + 고정값 power_output_thick)
  - fin_count는 정수로 써야 함 — 선형패턴 인스턴스 개수라 소수가 들어가면 리빌드가
    실패하거나 조용히 내림 처리된다. OLHD.to_dict()가 이미 int로 만들어 주지만,
    여기서도 한 번 더 확인해서 float가 흘러들어오면 바로 예외를 낸다.
  - 리빌드 후 핀 개수/갭을 로그에 남긴다 — 형상이 의도대로 나왔는지 눈으로 확인하려고.

⚠ SolidWorks 쪽 준비 (Equation Manager)
  핀 간격은 설계변수가 아니라 두께·개수에서 종속 계산되는 값이다. 파이썬이 갭을
  직접 써넣지 않고, SolidWorks가 수식으로 스스로 계산하게 둔다 — 두 곳에서 각각
  계산하면 언젠가 반드시 어긋나기 때문. paths.py 상단 주석의 수식을 참고할 것.
"""
import os

import pythoncom
import win32com.client

from OLHD import PARAM_NAMES, FIXED_PARAMS, INT_PARAMS
from fins import fin_gap, is_feasible, describe
from paths import PART_PATH, ASM_PATH, STEP_DIR

# SolidWorks에 실제로 써넣어야 하는 전역변수 전체 (자유변수 + 고정값)
SW_PARAM_NAMES = list(PARAM_NAMES) + list(FIXED_PARAMS)


def connect_sw():
    """SW 연결 및 어셈블리 열기"""
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("SldWorks.Application")
    app.Visible = True
    errors   = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    swDocASSEMBLY = 2
    model = app.OpenDoc6(ASM_PATH, swDocASSEMBLY, 1, "", errors, warnings)
    print("SW 연결 완료:", model.GetTitle)
    return app, errors, warnings


def _validate(params):
    """SolidWorks에 넣기 전 값 검증 — 잘못된 형상을 만들고 나서 알아채면 늦으므로."""
    missing = [n for n in SW_PARAM_NAMES if n not in params]
    if missing:
        raise KeyError(f"params에 빠진 변수: {missing}")

    for n in INT_PARAMS:
        v = params[n]
        if int(v) != v:
            raise ValueError(
                f"{n}={v} — 정수여야 함(선형패턴 인스턴스 개수). "
                "OLHD.to_dict()를 거치지 않고 만든 params일 가능성이 높음"
            )

    if not is_feasible(params["fin_thick"], params["fin_count"]):
        raise ValueError(
            f"갭 제약 위반: {describe(params['fin_thick'], params['fin_count'])} — "
            "이 조합은 애초에 제안되면 안 됨(OLHD.decode / ML 후보필터 확인)"
        )


def update_sw(app, errors, warnings, params):
    """
    글로벌 변수 업데이트 및 리빌드.
      params : {변수명: 값} — 키는 SolidWorks 글로벌 변수명과 정확히 일치해야 함.
               자유변수 9개 + 고정값(power_output_thick, fin_height)까지 전부 들어있어야 함.

    반환: (aluminum_mass_kg, aluminum_volume_mm3)
      유로(빈 공간)를 채운 PAO는 형상에 없는 개념이라 여기선 알 수 없음.
      대신 "채널이 하나도 안 뚫린 완전히 채워진 형상"의 부피(상수, FULL_SOLID_VOLUME_MM3)에서
      이번 알루미늄 부피를 빼면 PAO 부피가 나옴 — result_parser.py 참고.
    """
    _validate(params)

    part  = app.ActivateDoc3(PART_PATH, False, 0, errors)
    eqMgr = part.GetEquationMgr
    dispid = eqMgr._oleobj_.GetIDsOfNames("Equation")

    # 현재 수식 목록에서 '"이름"' → 인덱스 매핑
    name_to_i = {}
    for i in range(eqMgr.GetCount):
        lhs = eqMgr.Equation(i).split("=")[0].strip()
        name_to_i[lhs.strip('"')] = i

    missing = [n for n in SW_PARAM_NAMES if n not in name_to_i]
    if missing:
        raise KeyError(
            f"SolidWorks에 없는 글로벌 변수: {missing}\n"
            f"  현재 존재하는 변수: {sorted(name_to_i)}\n"
            f"  → Equation Manager의 변수명과 OLHD.PARAM_SPEC 이름을 일치시킬 것"
        )

    for name in SW_PARAM_NAMES:
        i = name_to_i[name]
        value = params[name]
        # fin_count는 "21.0"이 아니라 "21"로 써야 패턴 개수로 해석됨
        text = str(int(value)) if name in INT_PARAMS else str(value)
        eqMgr._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT,
                              False, i, '"%s" = %s' % (name, text))

    part.EditRebuild3
    part.Save3(1, errors, warnings)

    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.ForceRebuild3(False)
    asm.Save3(1, errors, warnings)

    print("SW 업데이트 완료: " + "  ".join(f"{k}={params[k]}" for k in SW_PARAM_NAMES))
    print(f"  {describe(params['fin_thick'], params['fin_count'])}")

    # 질량 특성 — 리빌드 직후 값이라 이번 params에 대응하는 형상의 질량/부피임
    #   asm.Extension.CreateMassProperty()는 이 환경에서 Extension 객체가 깨진 프록시로
    #   반환되어(COM 마샬링 문제로 추정) 동작하지 않음 — GetMassProperties(구버전 API,
    #   괄호 없이 접근)로 대체. 반환 튜플 순서는 GUI Mass Properties 패널 값과
    #   전부 대조 검증함: [0:3]=무게중심(m) [3]=부피(m^3) [4]=표면적(m^2) [5]=질량(kg)
    #   [6:12]=관성모멘트 Lxx,Lyy,Lzz,Lxy,Lxz,Lyz(kg·m^2)
    mp = asm.GetMassProperties
    aluminum_volume_mm3 = float(mp[3]) * 1e9   # m^3 → mm^3
    aluminum_mass_kg    = float(mp[5])         # kg
    print(f"  알루미늄 질량: {aluminum_mass_kg:.4f} kg  (부피: {aluminum_volume_mm3:.1f} mm^3)")
    return aluminum_mass_kg, aluminum_volume_mm3


def export_step(app, errors, idx):
    """STEP 파일 저장 후 경로 반환 (파일명은 idx 기준)

    형상↔파라미터 대응은 results_v5.csv가 유일한 기록 → ⚠ 이 파일 삭제 금지
    """
    os.makedirs(STEP_DIR, exist_ok=True)
    step_path = os.path.join(STEP_DIR, f"flowpath_{idx:03d}.STEP")
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.SaveAs3(step_path, 0, 0)
    print("STEP 저장 완료:", step_path)
    return step_path
