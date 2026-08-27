"""
V3 유로 8변수 — 메인 루프 (SW → Icepak → ML 순차 실행)

V2(Code/main.py) 대비 변경점
  - 로직 자체는 V2와 동일 — 바뀐 건 ML.py의 목적함수 정의(vel_cv_pass1/pass2 분리,
    max_temp 제외, 종료기준 3%)뿐이라 main.py는 손댈 이유가 없었음
  - 실행 전 seed_from_v2.py를 한 번 돌려서 results_v3.csv에 V2의 DOE 80개만
    이어받아두면, current_idx()가 80부터 시작해 곧바로 적응샘플링으로 진입함
    (DOE를 다시 밟지 않음 — SolidWorks/Icepak 새 해석 없이 기존 DOE 데이터 재사용).
    V2의 적응샘플링 284개(idx 80~363)는 옛 목적함수 기준으로 골라진 경로라
    일부러 이어받지 않음 — cv1/cv2 기준 불확실성탐색을 idx=80부터 새로 시작함

V1 대비 변경점(V2에서 이어짐)
  - 파라미터를 dict로 일괄 전달 (8개를 위치인자로 넘기지 않음)
  - 형상 리빌드 실패 시 캠페인 전체가 죽지 않고 해당 점을 failed_v3.csv에
    기록한 뒤 다음 점으로 진행
    · 8변수에서는 조합에 따라 형상이 성립하지 않을 수 있어 필요한 방어장치
  - ML의 private 함수(_load_results) 대신 public current_idx() 사용

이번 변경점 — AEDT 크래시 시 자동 재연결 + 같은 점 재시도
  - 실제로 121라운드째에 AEDT가 내부적으로 죽어(active_design이 None 반환)
    'NoneType' object has no attribute 'GetName' 에러가 났고, 그 뒤로 ipk가
    죽은 핸들인 채로 남아 이후 시도가 전부 같은 이유로 연쇄 실패 → 캠페인 종료됨
  - 이 실패들은 형상(설계 조합) 문제가 아니라 AEDT 프로세스 자체가 오래
    켜져 있으면서 누적된 내부 상태 문제로 보임 (변수값 자체는 전부 정상 범위)
    → SolidWorks 단계(형상 미성립)와 Icepak/AEDT 단계(환경 문제)를 분리해서,
      AEDT 쪽 실패는 재연결 후 같은 점을 다시 시도하도록 함
"""
from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from ML import get_next_params, update_ml, is_done, log_failure, current_idx
from result_parser import extract_and_save

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

MAX_CONSECUTIVE_FAIL = 5   # 연속 실패(형상 미성립 등)가 이만큼 쌓이면 설정 문제로 보고 중단
MAX_AEDT_RETRY = 3         # AEDT 크래시 시 같은 점을 재연결 후 재시도할 횟수
consecutive_fail = 0

while not is_done():
    params = get_next_params()
    idx    = current_idx()

    try:
        aluminum_mass_kg, aluminum_volume_mm3 = update_sw(app, errors, warnings, params)
        step_file = export_step(app, errors, idx)
    except Exception as e:
        # 형상 미성립 / 리빌드 실패 → 이 변수 조합 자체의 문제이므로 포기하고 다음 점으로
        log_failure(params, e)
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 형상 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    # Icepak/AEDT 단계 — 크래시는 이 실험점의 문제가 아니라 AEDT 자체 문제일 가능성이
    # 높으므로, 재연결 후 같은 점을 재시도함 (재시도를 다 써도 안 되면 그때만 포기)
    results = None
    for attempt in range(1, MAX_AEDT_RETRY + 1):
        try:
            # params 전달: 전원모듈 입구 측정면 높이가 power_input_thick에 따라 바뀜
            # pao_volume_mm3(icepak 반환값)는 중량 계산엔 안 쓰고 교차검증용 로그로만 사용
            ipk, result_path, _pao_volume_mm3_icepak = run_icepak(desktop, ipk, step_file, idx, params)
            results = extract_and_save(idx, params, result_path,
                                       aluminum_mass_kg, aluminum_volume_mm3)
            break
        except Exception as e:
            print(f"  ⚠ Icepak 실패 ({attempt}/{MAX_AEDT_RETRY}회차, AEDT 재연결 후 재시도): {e}")
            ipk = None
            desktop, ipk = connect_aedt()
            if attempt == MAX_AEDT_RETRY:
                log_failure(params, e)

    if results is None:
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    consecutive_fail = 0
    update_ml(params, results)   # results에 목적함수 4개 + 제약조건 2개 전부 들어있음

print("모든 실험 완료.")
input("종료하려면 엔터.")
