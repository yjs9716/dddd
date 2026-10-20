"""
1·2·4패스 기본 형상 재해석 — V6 해석 조건(발열 17개 × 40 W = 680 W, 출구 역류 차단)

초기 형상 비교(본론 ②)는 발열 9개(360 W) 조건이었다. 결론의 최적 형상과 같은 조건으로 맞추려고
세 형상을 icepak_pass.run_icepak_pass(캠페인 run_icepak 에서 2패스 전용 측정면만 뺀 복사본)로 다시 돌린다.
해석 설정(메시·물성·경계조건)은 캠페인과 같고, 발열원 온도와 팬 차압만 저장한다. 캠페인 코드는 건드리지 않는다.

사용법
  1) 아래 CASES 에 형상마다 STEP 경로와 전원모듈 입구 폭(power_input_thick)을 채운다.
     · 해석 설정은 캠페인과 완전히 같다. 형상만 STEP 으로 받는다.
     · power_input_thick 은 전원모듈 입구 국소 메시 박스 폭(x = −195 mm 부터) — STEP 형상의 실제 폭과 같게.
       통과 유량에 맞춰 정한다: 전원모듈이 직렬(전체 유량)이면 주 통로와 같은 19 mm, 분기면 5 mm.
     · 이름은 자유롭게 붙인다(예: "1pass_19mm"). 같은 이름을 다시 돌리면 그 줄만 덮어쓴다.
  2) F5(인자 없이)                            → 아래 RUN 에 적은 형상만 (RUN 이 비어 있으면 CASES 전부)
     python pass_compare.py 1pass_19mm       → 이름을 준 형상만 (RUN 무시)
  3) 결과: Result/PASS/results_pass.csv (형상별 최고온도·온도편차·차압 + 발열원별 평균·최고 온도)
           Result/PASS/result_pass_<이름>.csv (Icepak Fields Summary 원본)

⚠ 캠페인(main.py / run_forever.py)이 돌고 있을 때 실행하지 말 것 — 같은 AEDT 프로젝트 파일을 지우고 다시 만든다.
⚠ 1·4패스는 처음 한 번 AEDT 화면으로 팬(입구)·오프닝(출구) 면이 제대로 잡혔는지 확인할 것.
  해석은 PAO 유체 덩어리에서 z = 18.5 mm 면 두 개를 x 순서로 팬/오프닝으로 정한다(2패스 기준).

지표 정의는 result_parser 와 같다: 최고온도 = 발열원 Max 의 최댓값, 온도편차 = 발열원 Mean 의 표준편차(ddof=0),
차압 = Fan1_Passage 압력 Mean. (초기 비교의 2패스 0.29 K 도 같은 정의로 재현된다)
"""
import os
import sys
import time

import numpy as np
import pandas as pd

from icepak import connect_aedt, N_SOURCE
from icepak_pass import run_icepak_pass
from paths import RESULT_DIR

PASS_DIR = os.path.join(RESULT_DIR, "PASS")
SUMMARY_PATH = os.path.join(PASS_DIR, "results_pass.csv")

# ── 아침에 채울 곳 ─────────────────────────────────────────────
#   None 이 남아 있으면 실행하지 않는다.
#   형상 이름: {"step": STEP 경로, "power_input_thick": 전원모듈 입구 폭 [mm]}
CASES = {
    "1pass":      {"step": None, "power_input_thick": 5.0},    # 예: r"E:\...\flowpath_1pass.STEP"
    "1pass_19mm": {"step": None, "power_input_thick": 19.0},   # 1패스는 전원모듈 직렬 → 주 통로와 같은 폭
    "2pass":      {"step": None, "power_input_thick": 5.0},
    "4pass":      {"step": None, "power_input_thick": 5.0},
}

# F5(인자 없이) 실행할 형상 — 비워 두면 CASES 전부
RUN = ["1pass_19mm"]

# Fields Summary 열 (result_parser 와 같음)
COL_NAME, COL_MAX, COL_MEAN = 2, 8, 9


def _check(names):
    for n in names:
        c = CASES[n]
        if c.get("power_input_thick") is None:
            raise ValueError(f"[{n}] power_input_thick(전원모듈 입구 폭)을 채울 것")
        if not c.get("step"):
            raise ValueError(f"[{n}] STEP 경로를 채울 것")
        if not os.path.exists(c["step"]):
            raise FileNotFoundError(f"[{n}] STEP 파일 없음: {c['step']}")


# ── 결과 읽기: 발열원 온도 + 차압만 ───────────────────────────────
def _num(cell):
    try:
        return float(str(cell).strip().split()[0])
    except (ValueError, IndexError):
        return np.nan


def _parse(name, path):
    df = pd.read_csv(path, header=None, skiprows=5, sep=None, engine="python", on_bad_lines="skip")
    src = df.iloc[:N_SOURCE]
    bad = [str(n) for n in src[COL_NAME] if not str(n).strip().startswith("source")]
    if bad or str(df.iloc[N_SOURCE, COL_NAME]).strip() != "Fan1_Passage":
        raise ValueError(f"[{name}] CSV 행 순서가 예상과 다름 — 앞 {N_SOURCE}행 source, 다음 Fan1_Passage 여야 함")
    tmax = np.array([_num(v) for v in src[COL_MAX]])
    tmean = np.array([_num(v) for v in src[COL_MEAN]])
    dp = _num(df.iloc[N_SOURCE, COL_MEAN])
    if not (np.all(np.isfinite(tmax)) and np.all(np.isfinite(tmean)) and np.isfinite(dp)):
        raise ValueError(f"[{name}] 발열원 온도 또는 차압이 계산되지 않음(nan)")
    row = {"name": name, "max_temp": float(tmax.max()), "temp_std": float(np.std(tmean)),
           "pressure_drop": float(dp), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    row.update({f"mean_{i + 1:02d}": float(v) for i, v in enumerate(tmean)})
    row.update({f"max_{i + 1:02d}": float(v) for i, v in enumerate(tmax)})
    return row


def _save(row):
    old = pd.read_csv(SUMMARY_PATH) if os.path.exists(SUMMARY_PATH) else pd.DataFrame()
    if len(old):
        old = old[old["name"] != row["name"]]          # 같은 형상을 다시 돌리면 덮어씀
    pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(SUMMARY_PATH, index=False)


def main(names):
    names = names or RUN or list(CASES)
    unknown = [n for n in names if n not in CASES]
    if unknown:
        raise SystemExit(f"해당 형상 없음: {unknown} (가능: {list(CASES)})")
    _check(names)
    os.makedirs(PASS_DIR, exist_ok=True)

    desktop, ipk = connect_aedt()
    for k, n in enumerate(names):
        csv_path = os.path.join(PASS_DIR, f"result_pass_{n}.csv")
        print(f"\n===== {n} 해석 시작 ({k + 1}/{len(names)}) {time.strftime('%H:%M:%S')} =====")
        c = CASES[n]
        ipk, path = run_icepak_pass(desktop, ipk, c["step"], k, c["power_input_thick"], csv_path)
        row = _parse(n, path)
        row["power_input_thick"] = c["power_input_thick"]
        _save(row)
        print(f"[{n}] 최고온도 {row['max_temp']:.2f} °C  온도편차 {row['temp_std']:.3f} K  "
              f"차압 {row['pressure_drop']:.0f} Pa  → {SUMMARY_PATH}")

    print("\n완료:")
    print(pd.read_csv(SUMMARY_PATH)[["name", "power_input_thick", "max_temp", "temp_std", "pressure_drop", "time"]]
          .to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:])
