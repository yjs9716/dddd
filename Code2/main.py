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

이번 변경점 — 실패 원인을 구분해서 처리 + 실패 시 AEDT 프로젝트 정리
  배경이 된 두 가지 사고
    (1) 121라운드째 AEDT가 내부적으로 죽어(active_design이 None 반환)
        'NoneType' object has no attribute 'GetName' 에러 → ipk가 죽은 핸들로
        남아 이후 시도가 전부 연쇄 실패하며 캠페인 종료됨
    (2) 그 대응으로 "무제한 재시도"를 넣었더니, 이번엔 형상이 잘못 만들어진
        점(STEP 임포트 결과 바디가 2개 미만 → list index out of range)에서
        영원히 재시도하며 AEDT에 프로젝트만 90개 넘게 쌓임

  그래서 실패를 세 갈래로 나눠 처리함
    · 형상 리빌드 실패(SolidWorks 단계) : 기록하고 다음 점
    · AEDT 크래시(GetName/objectID 등)  : 재연결 후 같은 점 재시도 (MAX_AEDT_RETRY회)
    · 그 외 해석 실패(형상이 잘못 나온 경우 등) : 재시도해도 결과가 같으므로
      즉시 기록하고 다음 점 — 무한 재시도 방지

  추가로, 실패로 빠져나올 때 cleanup_projects()로 AEDT에 열린 프로젝트를 반드시
  닫음. run_icepak은 ipk가 살아있을 때만 이전 프로젝트를 닫는 구조라, 예외가 나면
  방금 만든 프로젝트가 그대로 남아 계속 누적되기 때문.
"""
from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from ML import get_next_params, update_ml, is_done, log_failure, current_idx
from result_parser import extract_and_save

# 연결 (한 번만)
app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

MAX_CONSECUTIVE_FAIL = 5   # 연속 실패가 이만큼 쌓이면 설정 문제로 보고 중단
MAX_AEDT_RETRY = 3         # AEDT 크래시일 때만 같은 점을 이 횟수까지 재시도
consecutive_fail = 0

# AEDT 프로세스가 죽었을 때 나타나는 에러들 — 이 경우에만 재연결 후 같은 점 재시도.
#   그 외(형상이 잘못 만들어져 바디 개수가 안 맞는 등)는 몇 번을 다시 해도 같은 결과라
#   재시도가 무의미하므로 바로 기록하고 다음 점으로 넘어감.
AEDT_CRASH_HINTS = ("GetName", "objectID", "Desktop", "CreateObject", "COM")


def cleanup_projects(desktop):
    """AEDT에 열린 채 남은 프로젝트를 전부 닫음.

    run_icepak은 시작할 때 ipk가 살아있어야만 기존 프로젝트를 닫는 구조라,
    예외로 빠져나오면 방금 만든 프로젝트가 AEDT 안에 열린 채로 남는다.
    이걸 정리하지 않으면 재시도할 때마다 프로젝트가 계속 쌓여 AEDT가 뻗는다.
    """
    try:
        od = desktop.odesktop
        for name in list(od.GetProjectList()):
            try:
                od.CloseProject(name)
            except Exception:
                pass
    except Exception:
        pass   # AEDT 자체가 죽어 정리 못 하는 경우 — 아래에서 재연결로 처리

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

    # Icepak/AEDT 단계 — 에러 성격에 따라 다르게 처리
    #   · AEDT 크래시  : AEDT 자체 문제이므로 재연결 후 같은 점을 재시도 (최대 MAX_AEDT_RETRY회)
    #   · 그 외의 실패 : 형상이 잘못 만들어진 경우 등 재시도해도 결과가 같으므로 즉시 다음 점으로
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
            # 실패로 빠져나오면 방금 만든 프로젝트가 AEDT에 열린 채 남으므로 반드시 정리
            cleanup_projects(desktop)
            ipk = None

            if not any(hint in str(e) for hint in AEDT_CRASH_HINTS):
                # 형상 문제 등 — 재시도 무의미
                print(f"  ⚠ 해석 실패 (형상/설정 문제로 판단, 재시도 없이 다음 점으로): {e}")
                log_failure(params, e)
                break

            print(f"  ⚠ AEDT 크래시 ({attempt}/{MAX_AEDT_RETRY}회차, 재연결 후 같은 점 재시도): {e}")
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
