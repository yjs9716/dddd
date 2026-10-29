"""
V7 메인 루프 — OLHD + GPR 적응샘플링 (SW → Icepak → 기록). V6 선별 결과(활성 8변수)를 그대로 쓴다.

전체 흐름
  ⓪ 캠페인 전 점검 (한 번)
       python grid_convergence.py   → 최종 조건(면 발열 17개, 680 W)에서 3단계 격자 + 같은 설계 재해석(재현성)
       결과를 보고 icepak.py 메시 값과 responses.TEMP_IN_KIND 를 확정한 뒤 캠페인을 시작한다 (WORKFLOW.md)
  ① OLHD + IMSE 적응샘플링 (활성 변수만)
       python main.py            → DOE 10×활성변수 → 적응샘플링 → 종료기준 충족 시 끝
       (무인 운전은 python run_forever.py)

  main.py 는 캠페인 상태(ML.campaign_state)를 보고 알아서 이어서 진행한다.
  선별 결과(screening_decision.json)가 없으면 멈추고 복사를 안내한다.

실패 처리
  · 형상 검증 실패(갭 제약·변수 누락 등) : 기록하고 다음 점
  · SolidWorks 오류(라이선스 회수·COM 끊김 등) : SW를 다시 띄워 같은 점 재시도 (MAX_SW_RETRY회)
  · AEDT 크래시·통신 오류(gRPC) : 재연결 후 같은 점 재시도 (MAX_AEDT_RETRY회)
  · 그 외 해석 실패 (열수지·측정면 점검 실패 포함, result_parser.py) : 기록하고 다음 점
  · 실패 기록은 지우지 않고 쌓인다. 실패한 DOE 점은 실패가 ML.MAX_FAIL_PER_POINT 회가 될 때까지
    다음 실험으로 다시 돌린다(ML._olhd_next)
"""
import os
import sys
import time

from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from result_parser import extract_and_save
import ML

app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

MAX_CONSECUTIVE_FAIL = 5
MAX_SW_RETRY = 3
SW_RETRY_WAIT_SEC = 30
MAX_AEDT_RETRY = 3
# 이 문구가 오류에 있으면 AEDT 쪽 일시 장애로 보고 재연결 후 같은 점을 재시도한다.
#   gRPC: "Failed to execute gRPC AEDT command: AnalyzeAll" — 해석 도중 AEDT 와의 통신이 끊긴 경우
AEDT_CRASH_HINTS = ("GetName", "objectID", "Desktop", "CreateObject", "COM", "gRPC")
consecutive_fail = 0

# 종료 코드 — run_forever.py(무인 운전)가 보고 다시 띄울지 정한다
EXIT_DONE, EXIT_RESTART, EXIT_NEED_HUMAN = 0, 2, 3
exit_code = EXIT_RESTART
SUPERVISED = os.environ.get("CAMPAIGN_SUPERVISED") == "1"   # run_forever.py 아래에서 돌 때


def reconnect_sw(app):
    """SolidWorks를 닫고 다시 띄운다 — 라이선스 회수 등으로 세션이 끊겼을 때 라이선스를 다시 받기 위함."""
    try:
        app.ExitApp()
    except Exception:
        pass
    time.sleep(SW_RETRY_WAIT_SEC)
    return connect_sw()


def cleanup_projects(desktop):
    try:
        od = desktop.odesktop
        for name in list(od.GetProjectList()):
            try:
                od.CloseProject(name)
            except Exception:
                pass
    except Exception:
        pass


while True:
    ML.clear_running()
    phase, idx, params = ML.next_job()
    if phase == "need_screening":
        print(f"\n선별 결과 파일이 없습니다: {ML.SCREENING_PATH}\n"
              "  V6 작업폴더의 Result\\DSD\\screening_decision.json 을 복사한 뒤 main.py 를 다시 실행하세요.")
        exit_code = EXIT_NEED_HUMAN
        break
    if phase == "done":
        print("\n종료기준 충족 — 캠페인 완료.")
        exit_code = EXIT_DONE
        break
    ML.mark_running(phase, idx, params)    # 이 실험 도중 프로세스가 죽으면 run_forever.py 가 실패로 기록

    t_round = time.time()
    tag = f"{phase}:{idx}"
    step_file = None
    for attempt in range(1, MAX_SW_RETRY + 1):
        try:
            aluminum_mass_kg, aluminum_volume_mm3 = update_sw(app, errors, warnings, params)
            step_file = export_step(app, errors, phase, idx)
            break
        except (ValueError, KeyError) as e:
            # 형상 자체의 문제(갭 제약 위반, 전역변수 누락) — 다시 해도 같으므로 재시도 없이 기록
            ML.log_failure(phase, idx, params, e)
            break
        except Exception as e:
            # SolidWorks 쪽 오류(라이선스 회수, COM 끊김 등) — SW를 다시 띄워 같은 점 재시도
            print(f"  ⚠ SolidWorks 오류 ({attempt}/{MAX_SW_RETRY}회차, SW 재시작 후 같은 점 재시도): {e}")
            try:
                app, errors, warnings = reconnect_sw(app)
            except Exception as e2:
                print(f"  ⚠ SolidWorks 재시작 실패: {e2}")
            if attempt == MAX_SW_RETRY:
                ML.log_failure(phase, idx, params, e)

    if step_file is None:
        ML.clear_running()                  # 실패는 이미 기록됨
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 형상 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    results = None
    for attempt in range(1, MAX_AEDT_RETRY + 1):
        try:
            ipk, result_path, pao_volume_mm3 = run_icepak(desktop, ipk, step_file, phase, idx, params)
            results = extract_and_save(tag, params, result_path, aluminum_mass_kg, aluminum_volume_mm3,
                                       pao_volume_mm3)
            break
        except Exception as e:
            cleanup_projects(desktop)
            ipk = None
            if not any(h in str(e) for h in AEDT_CRASH_HINTS):
                print(f"  ⚠ 해석 실패 (형상/설정 문제로 판단, 재시도 없이 다음 점으로): {e}")
                ML.log_failure(phase, idx, params, e)
                break
            print(f"  ⚠ AEDT 크래시·통신 오류 ({attempt}/{MAX_AEDT_RETRY}회차, 재연결 후 같은 점 재시도): {e}")
            try:
                desktop, ipk = connect_aedt()
            except Exception as e2:
                print(f"  ⚠ AEDT 재연결 실패 (다음 시도에서 다시): {e2}")
            if attempt == MAX_AEDT_RETRY:
                ML.log_failure(phase, idx, params, e)

    if results is None:
        ML.clear_running()                  # 실패는 이미 기록됨
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    consecutive_fail = 0
    ML.record(phase, idx, params, results)
    ML.clear_running()
    print(f"[{tag}] 이번 회차 총 소요 {time.time() - t_round:.0f}초\n")

ML.clear_running()
print("종료.")
if not SUPERVISED:
    input("종료하려면 엔터.")
sys.exit(exit_code)
