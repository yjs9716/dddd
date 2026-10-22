"""
V6 — SolidWorks COM 자동화 (전역변수 제어 + STEP 저장)

V5(Code/Solidworks.py) 대비 변경점
  · 전역변수 9개 → 후보 11개(params.CANDIDATES) 전부를 매 회차 써넣는다.
    2단계에서 선별로 고정된 변수도 SolidWorks에는 계속 전역변수로 남아 있으므로,
    고정값(screening_decision.json)을 매번 명시적으로 써넣는다 — 이전 회차 값이
    남아 있어 형상이 조용히 어긋나는 일을 막기 위함.
  · 핀 두께·개수가 뱅크별(fin_*_1 / fin_*_2)로 나뉘어 검증·로그도 뱅크별로 한다.
  · STEP 파일명이 단계별로 다르다(flowpath_dsd_000.STEP / flowpath_000.STEP).

나머지(연결, 리빌드, 질량 특성 추출)는 V5와 같다 — 근거는 V5 주석 참고.
"""
import pythoncom
import win32com.client

from params import CANDIDATES, INT_PARAMS
from fins import BANKS, bank_feasible, describe_bank
from paths import PART_PATH, ASM_PATH, step_path

SW_PARAM_NAMES = list(CANDIDATES)


def connect_sw():
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("SldWorks.Application")
    app.Visible = False
    errors   = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    swDocASSEMBLY = 2
    model = app.OpenDoc6(ASM_PATH, swDocASSEMBLY, 1, "", errors, warnings)
    app.Visible = False
    print("SW 연결 완료:", model.GetTitle)
    return app, errors, warnings


def _validate(params):
    missing = [n for n in SW_PARAM_NAMES if n not in params]
    if missing:
        raise KeyError(f"params에 빠진 변수: {missing}")
    for n in INT_PARAMS:
        if int(params[n]) != params[n]:
            raise ValueError(f"{n}={params[n]} — 정수여야 함(선형패턴 인스턴스 개수)")
    for b in BANKS:
        if not bank_feasible(params, b):
            raise ValueError(f"갭 제약 위반: {describe_bank(params, b)} — 이 조합은 제안되면 안 됨")


def update_sw(app, errors, warnings, params):
    """전역변수 11개 업데이트 및 리빌드. 반환: (aluminum_mass_kg, aluminum_volume_mm3)"""
    _validate(params)

    part  = app.ActivateDoc3(PART_PATH, False, 0, errors)
    eqMgr = part.GetEquationMgr
    dispid = eqMgr._oleobj_.GetIDsOfNames("Equation")

    name_to_i = {}
    for i in range(eqMgr.GetCount):
        lhs = eqMgr.Equation(i).split("=")[0].strip()
        name_to_i[lhs.strip('"')] = i

    missing = [n for n in SW_PARAM_NAMES if n not in name_to_i]
    if missing:
        raise KeyError(
            f"SolidWorks에 없는 전역변수: {missing}\n"
            f"  현재 존재하는 변수: {sorted(name_to_i)}\n"
            "  → paths.py 상단 '시작 전 준비'의 변수 11개와 뱅크별 갭 수식을 Equation Manager에 만들 것")

    for name in SW_PARAM_NAMES:
        value = params[name]
        text = str(int(value)) if name in INT_PARAMS else str(value)
        eqMgr._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT,
                              False, name_to_i[name], '"%s" = %s' % (name, text))

    part.EditRebuild3
    part.Save3(1, errors, warnings)

    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.ForceRebuild3(False)
    asm.Save3(1, errors, warnings)

    print("SW 업데이트 완료: " + "  ".join(f"{k}={params[k]}" for k in SW_PARAM_NAMES))
    for b in BANKS:
        print(f"  {describe_bank(params, b)}")

    mp = asm.GetMassProperties          # [3]=부피(m^3) [5]=질량(kg) — V5에서 GUI 값과 대조 검증
    aluminum_volume_mm3 = float(mp[3]) * 1e9
    aluminum_mass_kg    = float(mp[5])
    print(f"  알루미늄 질량: {aluminum_mass_kg:.4f} kg  (부피: {aluminum_volume_mm3:.1f} mm^3)")
    return aluminum_mass_kg, aluminum_volume_mm3


def export_step(app, errors, phase, idx):
    """STEP 저장 후 경로 반환. 형상↔파라미터 대응은 결과 CSV가 유일한 기록 → 삭제 금지."""
    path = step_path(phase, idx)
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.SaveAs3(path, 0, 0)
    print("STEP 저장 완료:", path)
    return path
