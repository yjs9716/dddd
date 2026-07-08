from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from ML import get_next_params, update_ml, is_done
from result_parser import extract_and_save

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

# 메인 루프
while not is_done():
    angle, thickness = get_next_params()
    update_sw(app, errors, warnings, angle, thickness)
    step_file = export_step(app, errors, angle, thickness)

    # idx는 현재까지 완료된 실험 수 기준
    from ML import _load_results
    idx = len(_load_results())

    ipk, result_path, speed_path = run_icepak(desktop, ipk, step_file, idx)
    max_temp, temp_std, pressure_drop, vel_cv = extract_and_save(idx, angle, thickness, result_path, speed_path)
    update_ml(angle, thickness, pressure_drop, vel_cv, max_temp, temp_std)
    print(f"[{idx}] 각도:{angle} 두께:{thickness} 차압:{pressure_drop} 속도CV:{vel_cv:.4f}%")

print("모든 실험 완료.")
input("종료하려면 엔터.")
