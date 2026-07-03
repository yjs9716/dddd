from Solidworks import connect_sw, update_sw, export_step
from icepak_final import connect_aedt, run_icepak
from ML_final import get_next_params, update_ml, is_done
from result_parser import extract_and_save

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

# 메인 루프 (results.csv 기준으로 이어서 실행됨)
while not is_done():
    idx, angle, thickness = get_next_params()

    update_sw(app, errors, warnings, angle, thickness)
    step_file = export_step(app, errors, angle, thickness)

    ipk, result_path = run_icepak(desktop, ipk, step_file, idx)

    max_temp, temp_std, pressure_drop = extract_and_save(idx, angle, thickness, result_path)
    update_ml(idx, angle, thickness, max_temp, temp_std, pressure_drop)

    print(f"[{idx}] 각도:{angle} 두께:{thickness} 최대온도:{max_temp} 온도std:{temp_std} 차압:{pressure_drop}")

print("모든 실험 완료.")
input("종료하려면 엔터.")
