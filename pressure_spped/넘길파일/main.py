"""
V2 유로 7변수 — 메인 루프 (SW → Icepak → ML 순차 실행)

V1 대비 변경점
  - 파라미터를 dict로 일괄 전달 (7개를 위치인자로 넘기지 않음)
  - 형상 리빌드/해석 실패 시 캠페인 전체가 죽지 않고 해당 점을 failed_v2.csv에
    기록한 뒤 다음 점으로 진행
    · 7변수에서는 조합에 따라 형상이 성립하지 않을 수 있어 필요한 방어장치
  - ML의 private 함수(_load_results) 대신 public current_idx() 사용
"""
from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from ML import get_next_params, update_ml, is_done, log_failure, current_idx
from result_parser import extract_and_save

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

MAX_CONSECUTIVE_FAIL = 5   # 연속 실패가 이만큼 쌓이면 설정 문제로 보고 중단
consecutive_fail = 0

while not is_done():
    params = get_next_params()
    idx    = current_idx()

    try:
        update_sw(app, errors, warnings, params)
        step_file = export_step(app, errors, idx)
        ipk, result_path = run_icepak(desktop, ipk, step_file, idx)
        results = extract_and_save(idx, params, result_path)
    except Exception as e:
        # 형상 미성립 / 리빌드 실패 / 해석 실패 → 기록하고 다음 점으로
        log_failure(params, e)
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    consecutive_fail = 0
    update_ml(params, results,
              max_temp=results["max_temp"], temp_std=results["temp_std"])
    print(f"[{idx}] 차압:{results['pressure_drop']} 속도CV:{results['vel_cv']:.4f}%")

print("모든 실험 완료.")
input("종료하려면 엔터.")
