from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from ML import get_next_params, update_ml, is_done

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

# 메인 루프
#while not is_done():
 #   angle, thickness = get_next_params()
  #  update_sw(app, errors, warnings, angle, thickness)
   # step_file = export_step(app, errors, angle, thickness)
    #result = run_icepak(ipk, step_file)
    #update_ml(angle, thickness, result)
    #print(f"각도:{angle} 두께:{thickness} 결과:{result}")

for _ in range(1):
    angle, thickness = get_next_params()
    update_sw(app, errors, warnings, angle, thickness)
    step_file = export_step(app, errors, angle, thickness)
    ipk, result = run_icepak(desktop, ipk, step_file)
    update_ml(angle, thickness, result)
    print(f"각도:{angle} 두께:{thickness} 결과:{result}")

input("작업 완료. 종료하려면 엔터.")    # ← 이게 AEDT를 살려둠
