"""
V3 유로 8변수 — 메인 루프 (SW → Icepak → ML 순차 실행)

V2(Code/main.py) 대비 변경점
  - 로직 자체는 V2와 동일 — 바뀐 건 ML.py의 목적함수 정의(vel_cv_pass1/pass2 분리,
    max_temp 제외, 종료기준 3%)뿐이라 main.py는 손댈 이유가 없었음
  - 실행 전 seed_from_v2.py를 한 번 돌려서 results_v3.csv에 V2의 364개 결과를
    이어받아두면, current_idx()가 364부터 시작해 곧바로 적응샘플링으로 진입함
    (DOE를 다시 밟지 않음 — SolidWorks/Icepak 새 해석 없이 기존 데이터 재사용)

V1 대비 변경점(V2에서 이어짐)
  - 파라미터를 dict로 일괄 전달 (8개를 위치인자로 넘기지 않음)
  - 형상 리빌드/해석 실패 시 캠페인 전체가 죽지 않고 해당 점을 failed_v3.csv에
    기록한 뒤 다음 점으로 진행
    · 8변수에서는 조합에 따라 형상이 성립하지 않을 수 있어 필요한 방어장치
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
        aluminum_mass_kg, aluminum_volume_mm3 = update_sw(app, errors, warnings, params)
        step_file = export_step(app, errors, idx)
        # params 전달: 전원모듈 입구 측정면 높이가 power_input_thick에 따라 바뀜
        # pao_volume_mm3(icepak 반환값)는 중량 계산엔 안 쓰고 교차검증용 로그로만 사용
        ipk, result_path, _pao_volume_mm3_icepak = run_icepak(desktop, ipk, step_file, idx, params)
        results = extract_and_save(idx, params, result_path,
                                   aluminum_mass_kg, aluminum_volume_mm3)
    except Exception as e:
        # 형상 미성립 / 리빌드 실패 / 해석 실패 → 기록하고 다음 점으로
        log_failure(params, e)
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    consecutive_fail = 0
    update_ml(params, results)   # results에 목적함수 4개 + 제약조건 2개 전부 들어있음

print("모든 실험 완료.")
input("종료하려면 엔터.")
