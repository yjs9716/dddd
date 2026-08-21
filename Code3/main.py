"""
V4 유로 8변수 — 메인 루프 (SW → Icepak → ML 순차 실행)

V3(Code2/main.py) 대비 변경점
  - 로직은 V3와 동일. 바뀐 건 ML.py/result_parser.py의 학습 대상 정의뿐이라
    main.py는 손댈 이유가 없었음 (실패 처리·재시도·프로젝트 정리 그대로 유지)
  - 작업폴더가 260821로 바뀌므로 paths.py만 새로 씀
  - V4는 idx=0부터 시작함. results_v4.csv가 비어 있으면 DOE 80점부터 밟고,
    seed_from_raw.py로 과거 레인값을 복원해둔 경우엔 그 다음 번호부터 이어감

실패 처리 (V3에서 그대로 이어짐)
  · 형상 리빌드 실패(SolidWorks 단계) : 기록하고 다음 점
  · AEDT 크래시(GetName/objectID 등)  : 재연결 후 같은 점 재시도 (MAX_AEDT_RETRY회)
  · 그 외 해석 실패(형상이 잘못 나온 경우 등) : 재시도해도 결과가 같으므로
    즉시 기록하고 다음 점 — 무한 재시도 방지
  실패로 빠져나올 때는 cleanup_projects()로 AEDT에 열린 프로젝트를 반드시 닫음
  (run_icepak은 ipk가 살아있을 때만 이전 프로젝트를 닫는 구조라, 예외가 나면
   방금 만든 프로젝트가 그대로 남아 계속 누적되기 때문)
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
    """AEDT에 열린 채 남은 프로젝트를 전부 닫음."""
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
    update_ml(params, results)   # results에 레인 14개 + 목적함수 3개 + 제약조건 2개 전부 들어있음

print("모든 실험 완료.")
input("종료하려면 엔터.")
