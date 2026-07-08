# 메인 루프 — 목적함수: 차압 + 핀뱅크 입구 속도CV (main_final.py 기반)
# 실행 위치: pressure_spped 폴더 (부모 폴더의 Solidworks/icepak_final을 그대로 재사용)
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_HERE)                        # sheets, postprocess, ml_ps
sys.path.append(os.path.dirname(_HERE))       # Solidworks, icepak_final, OLHD

from Solidworks import connect_sw, update_sw, export_step
from icepak_final import connect_aedt, run_icepak
from sheets import create_inlet_sheets
from postprocess import export_speed_csv, parse_speed_csv, parse_result_csv
from ml_ps import get_next_params, update_ml, is_done, _load_results

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

# 메인 루프
while not is_done():
    angle, thickness = get_next_params()
    update_sw(app, errors, warnings, angle, thickness)
    step_file = export_step(app, errors, angle, thickness)

    # idx는 현재까지 완료된 실험 수 기준
    idx = len(_load_results())

    # 해석 + 기존 온도/차압 CSV export (run_icepak 내부에서 수행)
    ipk, result_path = run_icepak(desktop, ipk, step_file, idx)
    max_temp, temp_std, pressure_drop = parse_result_csv(result_path)

    # 30개 시트 생성 → 속도 export → CV 계산 (Solve 후, NonModel이라 결과 영향 없음)
    # 시트 생성을 icepak 실행 로직(run_icepak) 안에 직접 포함시킨 경우
    # 이미 존재하므로 여기서는 자동으로 건너뜀 (이름 충돌 방지)
    oDesign = ipk.odesign
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    if "V_inlet_01" not in ipk.modeler.object_names:
        create_inlet_sheets(oEditor)
    speed_path = export_speed_csv(oDesign, idx)
    speeds, vel_cv = parse_speed_csv(speed_path)

    # 기록: 목적함수(차압, CV) + 기록용(온도)
    update_ml(angle, thickness, pressure_drop, vel_cv, max_temp, temp_std)
    print(f"[{idx}] 각도:{angle} 두께:{thickness} 차압:{pressure_drop} 속도CV:{vel_cv:.4f}%"
          f" (기록용 — 최대온도:{max_temp} 온도std:{temp_std})")

print("모든 실험 완료.")
input("종료하려면 엔터.")
