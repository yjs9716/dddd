"""
캠페인 무인 운전 — main.py 를 자식 프로세스로 돌리며, 어떤 이유로 꺼지거나 멈춰도 다시 띄운다.

사용
  python run_forever.py          (main.py 대신 이것을 실행. 끝낼 때는 이 창에서 Ctrl+C)

하는 일
  · main.py 가 꺼지면 이유를 보고 판단한다
      - 캠페인 완료(종료 코드 0)            → 감시도 끝냄
      - 사람이 봐야 하는 상태(종료 코드 3)   → 감시도 끝냄 (DSD 판정 필요 등)
      - 그 외 전부 (오류로 죽음, AEDT·SolidWorks 와 함께 죽음, 연속 실패로 중단 등) → 다시 띄움
  · 멈춤 감지: HANG_HOURS 시간 동안 main.py 출력이 한 줄도 없으면 멈춘 것으로 보고 강제 종료 후 다시 띄운다
      (실험 1회 30~50분. AEDT 팝업 대기 같은 먹통 대비)
  · 다시 띄우기 전에 남아 있는 AEDT·SolidWorks 를 강제 종료한다 (반쯤 죽은 프로그램에 다시 붙지 않게)
      ⚠ 이 PC 의 AEDT·SolidWorks 가 전부 꺼진다 — 캠페인 중에는 같은 PC 에서 따로 쓰지 말 것
  · 해석 도중 죽은 점은 실패로 기록한다(ML.load_running). 실패가 ML.MAX_FAIL_PER_POINT 회가 되면 그 점은
    건너뛰므로, 특정 점에서 계속 죽어도 무한 반복하지 않는다
  · 연달아 죽으면 기다리는 시간을 늘린다 (1 → 5 → 15 → 30 → 60분). 사이에 실험이 하나라도 진행됐으면 1분부터 다시
  · 기록: run_forever.log (재시작 이력), campaign_console.log (main.py 출력 전체) — 둘 다 이 폴더

PC 절전·윈도우 업데이트 재부팅은 막지 못한다. 절전은 끄고, 필요하면 작업 스케줄러에 로그온 시 실행으로 건다.
"""
import datetime
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(HERE, "main.py")
LOG_PATH = os.path.join(HERE, "run_forever.log")
CONSOLE_LOG_PATH = os.path.join(HERE, "campaign_console.log")

HANG_HOURS = 2.0                                  # 출력이 이 시간 동안 없으면 멈춤으로 판단
BACKOFF_MIN = [1, 5, 15, 30, 60]                  # 연달아 비정상 종료될 때 다시 띄우기 전 대기 [분]
POLL_SEC = 30                                     # 멈춤 확인 주기 [초]
KILL_IMAGES = ["ansysedt.exe", "SLDWORKS.exe"]    # 다시 띄우기 전 강제 종료할 프로그램 (윈도우 이미지 이름)

EXIT_DONE, EXIT_RESTART, EXIT_NEED_HUMAN = 0, 2, 3   # main.py 와 같은 값
_child = None                                       # 지금 돌고 있는 main.py (Ctrl+C 때 함께 종료)

try:
    sys.stdout.reconfigure(errors="replace")      # 콘솔이 못 찍는 글자(⚠ 등) 때문에 감시가 죽지 않게
except Exception:
    pass


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] [감시] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def kill_tree(pid):
    """자식 프로세스와 그 아래 프로세스 전부 강제 종료."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(pid, 9)
        except Exception:
            pass


def kill_apps():
    """남아 있는 AEDT·SolidWorks 강제 종료 (윈도우에서만)."""
    if os.name != "nt":
        return
    for image in KILL_IMAGES:
        r = subprocess.run(["taskkill", "/IM", image, "/T", "/F"], capture_output=True, text=True)
        if r.returncode == 0:
            log(f"{image} 강제 종료")


def progress_count():
    """성공 기록 건수 — 한 번 띄운 사이에 실험이 실제로 진행됐는지 판단용 (실패만 쌓인 건 진행으로 보지 않음)."""
    import ML
    return len(ML._load_results())


def record_crash(reason):
    """main.py 가 해석 도중 죽었으면 그 점을 실패로 기록 (이미 성공으로 기록된 점이면 건너뜀)."""
    import ML
    job = ML.load_running()
    if not job:
        return
    params = job["params"]
    done = ML._load_results()
    if job["phase"] != "dsd" and ML._n_matches(done, [params[n] for n in ML.CANDIDATES]):
        log(f"중단된 점({job['phase']}:{job['idx']})은 이미 결과가 기록돼 있음 — 실패로 남기지 않음")
    else:
        ML.log_failure(job["phase"], job["idx"], params, f"{reason} (시작 {job.get('start', '?')})")
        log(f"해석 도중 중단된 점({job['phase']}:{job['idx']})을 실패로 기록: {reason}")
    ML.clear_running()


def run_once():
    """main.py 를 한 번 띄워 끝날 때까지 지켜본다. 반환: 종료 코드, 또는 멈춤이면 'hang'."""
    env = {**os.environ, "CAMPAIGN_SUPERVISED": "1", "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    global _child
    p = subprocess.Popen([sys.executable, "-u", MAIN_SCRIPT], cwd=os.path.dirname(MAIN_SCRIPT), env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", **kwargs)
    _child = p
    last_output = [time.time()]

    def pump():
        with open(CONSOLE_LOG_PATH, "a", encoding="utf-8") as f:
            for line in p.stdout:
                last_output[0] = time.time()
                print(line, end="", flush=True)
                f.write(line)
                f.flush()

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    while p.poll() is None:
        time.sleep(POLL_SEC)
        if time.time() - last_output[0] > HANG_HOURS * 3600:
            log(f"main.py 출력이 {HANG_HOURS:g}시간 동안 없음 — 멈춘 것으로 보고 강제 종료")
            kill_tree(p.pid)
            p.wait()
            reader.join(timeout=10)
            return "hang"
    reader.join(timeout=10)
    return p.returncode


def main():
    log(f"무인 운전 시작 (멈춤 판단 {HANG_HOURS:g}시간, 재시작 대기 {BACKOFF_MIN}분)")
    n_bad = 0
    while True:
        before = progress_count()
        log("main.py 시작")
        rc = run_once()
        if rc == EXIT_DONE:
            log("캠페인 완료 — 무인 운전 종료")
            return
        if rc == EXIT_NEED_HUMAN:
            log("사람이 확인해야 하는 상태로 main.py 종료 — 무인 운전 종료 (콘솔 기록 확인)")
            return
        if rc == "hang":
            reason = f"멈춤({HANG_HOURS:g}시간 출력 없음)으로 강제 종료"
        elif rc == EXIT_RESTART:
            reason = "main.py 가 연속 실패로 스스로 중단"
        else:
            reason = f"main.py 비정상 종료 (종료 코드 {rc})"
        log(reason)
        kill_apps()
        record_crash(reason)
        n_bad = 1 if progress_count() > before else n_bad + 1     # 성공이 하나라도 늘었으면 대기를 처음부터
        wait = BACKOFF_MIN[min(n_bad, len(BACKOFF_MIN)) - 1]
        log(f"{wait}분 뒤 다시 시작 (연속 비정상 종료 {n_bad}회)")
        time.sleep(wait * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if _child is not None and _child.poll() is None:
            kill_tree(_child.pid)       # main.py 는 따로 된 프로세스 그룹이라 Ctrl+C 가 전달되지 않음
        log("사용자가 Ctrl+C 로 무인 운전 종료 (돌던 main.py 도 종료, 그 점은 다음 실행 때 다시 해석)")
