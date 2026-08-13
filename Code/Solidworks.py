"""
V2 유로 7변수 — SolidWorks COM 자동화 (글로벌 변수 제어 + STEP 저장)

V1 대비 변경점
  - 글로벌 변수 2개(각도/유로두께) → 7개, params dict로 일괄 처리
  - set_value 실패(해당 이름의 수식이 없음)를 감지해서 예외 발생
    · V1은 이름이 안 맞아도 조용히 넘어가서, 형상이 안 바뀐 채 해석이 도는 사고가 가능했음
  - STEP 파일명: 파라미터 7개를 다 넣으면 경로가 너무 길어져 idx 기준으로 변경
    · 형상↔파라미터 대응은 results_v2.csv가 유일한 기록 → ⚠ 이 파일 삭제 금지
"""
import os

import pythoncom
import win32com.client

from OLHD import PARAM_NAMES
from paths import PART_PATH, ASM_PATH, STEP_DIR


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


def update_sw(app, errors, warnings, params):
    """
    글로벌 변수 7개 업데이트 및 리빌드.
      params : {변수명: 값} — 키는 SolidWorks 글로벌 변수명과 정확히 일치해야 함

    반환: (aluminum_mass_kg, aluminum_volume_mm3)
      유로(빈 공간)를 채운 PAO는 형상에 없는 개념이라 여기선 알 수 없음.
      대신 "채널이 하나도 안 뚫린 완전히 채워진 형상"의 부피(상수, FULL_SOLID_VOLUME_MM3)에서
      이번 알루미늄 부피를 빼면 PAO 부피가 나옴 — result_parser.py 참고.
      (Icepak을 따로 안 돌려도 SolidWorks만으로 총 중량 계산 가능)
    """
    part  = app.ActivateDoc3(PART_PATH, False, 0, errors)
    eqMgr = part.GetEquationMgr
    dispid = eqMgr._oleobj_.GetIDsOfNames("Equation")

    # 현재 수식 목록에서 '"이름"' → 인덱스 매핑
    name_to_i = {}
    for i in range(eqMgr.GetCount):
        lhs = eqMgr.Equation(i).split("=")[0].strip()
        name_to_i[lhs.strip('"')] = i

    missing = [n for n in params if n not in name_to_i]
    if missing:
        raise KeyError(
            f"SolidWorks에 없는 글로벌 변수: {missing}\n"
            f"  현재 존재하는 변수: {sorted(name_to_i)}\n"
            f"  → Equation Manager의 변수명과 OLHD.PARAM_SPEC 이름을 일치시킬 것"
        )

    for name, value in params.items():
        i = name_to_i[name]
        eqMgr._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT,
                              False, i, '"%s" = %s' % (name, value))

    part.EditRebuild3
    part.Save3(1, errors, warnings)

    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.ForceRebuild3(False)
    asm.Save3(1, errors, warnings)
    print("SW 업데이트 완료: " + "  ".join(f"{k}={v}" for k, v in params.items()))

    # 질량 특성 — 리빌드 직후 값이라 이번 params에 대응하는 형상의 질량/부피임
    mass_prop = asm.Extension.CreateMassProperty()
    aluminum_mass_kg    = float(mass_prop.Mass)             # SolidWorks API는 SI(kg) 반환
    aluminum_volume_mm3 = float(mass_prop.Volume) * 1e9     # SI(m^3) → mm^3
    print(f"  알루미늄 질량: {aluminum_mass_kg:.4f} kg  (부피: {aluminum_volume_mm3:.1f} mm^3)")
    return aluminum_mass_kg, aluminum_volume_mm3


def export_step(app, errors, idx):
    """STEP 파일 저장 후 경로 반환 (파일명은 idx 기준)"""
    os.makedirs(STEP_DIR, exist_ok=True)
    step_path = os.path.join(STEP_DIR, f"flowpath_{idx:03d}.STEP")
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.SaveAs3(step_path, 0, 0)
    print("STEP 저장 완료:", step_path)
    return step_path
