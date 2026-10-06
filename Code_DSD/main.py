"""
V6 메인 루프 — DSD 선별 → OLHD + GPR 적응샘플링 (SW → Icepak → 기록)

전체 흐름
  ① 1단계 DSD (후보 11변수 + 가짜 인자 3열, 29회)
       python main.py            → dsd_plan.csv 의 run 0~28 을 순서대로 해석
  ② 선별 판정
       python DSD_analysis.py    → dsd_effects.csv, screening_decision.json
       (판정 규칙은 DSD_analysis.py 상단 "사전 고정 규칙" — DSD 시작 전에 확정할 것)
  ③ 2단계 OLHD + IMSE 적응샘플링 (활성 변수만)
       python main.py            → DOE 10×활성변수 → 적응샘플링 → 종료기준 충족 시 끝

  main.py 는 캠페인 상태(ML.campaign_state)를 보고 알아서 이어서 진행한다.
  DSD가 끝났는데 선별 판정이 아직 없으면 멈추고 ②를 안내한다 — 자동으로 넘어가지 않는다.

실패 처리 (V5와 동일)
  · 형상 리빌드 실패 : 기록하고 다음 점
  · AEDT 크래시      : 재연결 후 같은 점 재시도 (MAX_AEDT_RETRY회)
  · 그 외 해석 실패  : 기록하고 다음 점
  ⚠ DSD 단계는 한 run 이라도 빠지면 분석할 수 없다. 실패한 run 은 failed_dsd.csv 에 남고,
    원인을 고친 뒤 `python -c "import ML; ML.retry_failed_dsd()"` 로 다시 시도 목록에 올린다.

⚠ 첫 실행 전 확인 (V6에서 형상이 바뀌었으므로)
  1) SolidWorks 전역변수 11개 + 뱅크별 갭 수식 (paths.py 상단)
  2) icepak.py 의 FIN_BANK1/2_Y_START — 측정면이 두 뱅크 유로 안에 정확히 들어가는지
     DSD run 0 을 AEDT 화면으로 직접 볼 것 (뱅크별 핀 개수가 달라짐)
  3) result_parser.py 의 FULL_SOLID_VOLUME_MM3 — 판재 외형이 바뀌었으면 다시 실측
"""
import time

from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from result_parser import extract_and_save
import ML

app, errors, warnings = connect_sw()
desktop, ipk = connect_aedt()

MAX_CONSECUTIVE_FAIL = 5
MAX_AEDT_RETRY = 3
AEDT_CRASH_HINTS = ("GetName", "objectID", "Desktop", "CreateObject", "COM")
consecutive_fail = 0


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
    phase, idx, params = ML.next_job()
    if phase == "need_screening":
        print("\nDSD 29회 완료. `python DSD_analysis.py` 로 선별 판정을 확정한 뒤 main.py 를 다시 실행하세요.")
        break
    if phase == "dsd_blocked":
        print(f"\nDSD 남은 run 이 모두 실패 기록 상태입니다: {ML.dsd_missing_runs()}\n"
              "  원인을 고친 뒤 ML.retry_failed_dsd() 로 재시도 목록에 올리세요.")
        break
    if phase == "done":
        print("\n종료기준 충족 — 2단계 완료.")
        break

    t_round = time.time()
    tag = f"{phase}:{idx}"
    try:
        aluminum_mass_kg, aluminum_volume_mm3 = update_sw(app, errors, warnings, params)
        step_file = export_step(app, errors, phase, idx)
    except Exception as e:
        ML.log_failure(phase, idx, params, e)
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 형상 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    results = None
    for attempt in range(1, MAX_AEDT_RETRY + 1):
        try:
            ipk, result_path, _ = run_icepak(desktop, ipk, step_file, phase, idx, params)
            results = extract_and_save(tag, params, result_path, aluminum_mass_kg, aluminum_volume_mm3)
            break
        except Exception as e:
            cleanup_projects(desktop)
            ipk = None
            if not any(h in str(e) for h in AEDT_CRASH_HINTS):
                print(f"  ⚠ 해석 실패 (형상/설정 문제로 판단, 재시도 없이 다음 점으로): {e}")
                ML.log_failure(phase, idx, params, e)
                break
            print(f"  ⚠ AEDT 크래시 ({attempt}/{MAX_AEDT_RETRY}회차, 재연결 후 같은 점 재시도): {e}")
            desktop, ipk = connect_aedt()
            if attempt == MAX_AEDT_RETRY:
                ML.log_failure(phase, idx, params, e)

    if results is None:
        consecutive_fail += 1
        if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
            print(f"\n연속 {MAX_CONSECUTIVE_FAIL}회 실패 — 변수 범위나 설정을 점검하세요.")
            break
        continue

    consecutive_fail = 0
    ML.record(phase, idx, params, results)
    print(f"[{tag}] 이번 회차 총 소요 {time.time() - t_round:.0f}초\n")

print("종료.")
input("종료하려면 엔터.")
