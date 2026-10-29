"""
V7 — 1·2·4패스 기본 형상 비교 (V6 pass_compare.py 기반, V7 해석 조건: 면 발열 17개 × 40 W = 680 W, 4 LPM)

V6 대비 변경점
  · 해석은 캠페인과 같은 icepak.run_icepak 을 measure=False 로 부른다 — 2패스 전용 측정면만 빼고 메시·물성·
    경계조건이 캠페인과 한 줄도 다르지 않다(V6 처럼 복사본 icepak_pass.py 를 따로 두지 않는다).
  · 지표는 result_parser 와 같은 정의(발열면 17개):
      max_temp(최고온도) · temp_std(채널 간 = 평균 17개의 표준편차) · temp_in_range / temp_in_sd(채널 안) ·
      temp_in_worst · pressure_drop(팬 차압) · 열수지(출구 온도로 본 흡열 ÷ 680 W)
  · 끝에 COMPARE 순서대로 "패스를 늘릴 때 차압 증가 대비 온도 이득"을 표로 낸다 — 2패스를 고르는 논리
    (1 → 2 는 차압을 조금 더 쓰고 온도를 크게 얻고, 2 → 4 는 차압을 크게 더 쓰고 온도를 조금 얻는지).

사용법
  1) 아래 CASES 에 형상마다 STEP 경로와 전원모듈 입구 폭(power_input_thick)을 채운다.
     · power_input_thick 은 전원모듈 입구 국소 메시 박스 폭(x = −195 mm 부터) — STEP 형상의 실제 폭과 같게.
       전원모듈이 직렬(전체 유량)이면 주 통로와 같은 19 mm, 분기면 5 mm.
     · 이름은 자유롭게 붙인다. 같은 이름을 다시 돌리면 그 줄만 덮어쓴다.
  2) F5(인자 없이)                       → 아래 RUN 에 적은 형상만 (RUN 이 비어 있으면 STEP 을 채운 CASES 전부)
     python pass_compare.py 2pass 4pass → 이름을 준 형상만
     python pass_compare.py report      → 해석 없이 표만 다시
  3) 결과: Result/PASS/results_pass.csv (형상별 지표 + 발열면별 평균·최고·최저 온도)
           Result/PASS/result_pass_<이름>.csv (Icepak Fields Summary 원본)

⚠ 캠페인(main.py / run_forever.py)·verify_point.py·grid_convergence.py 가 돌고 있을 때 실행하지 말 것 —
  같은 AEDT 프로젝트 파일을 지우고 다시 만든다.
⚠ 1·4패스는 처음 한 번 AEDT 화면으로 팬(입구)·오프닝(출구) 면이 제대로 잡혔는지 확인할 것.
  해석은 PAO 유체 덩어리에서 z = 18.5 mm 면 두 개를 x 순서로 팬(큰 x)/오프닝(작은 x)으로 정한다(2패스 기준).
"""
import os
import sys
import time

import numpy as np
import pandas as pd

import icepak
from icepak import connect_aedt, N_SOURCE
from result_parser import _columns, _num, SKIP_ROWS, COL_NAME, HEAT_CAPACITY_W_PER_K, TOTAL_HEAT_W, HEAT_BALANCE_WARN
from icepak import INLET_TEMP_C
from paths import RESULT_DIR

PASS_DIR = os.path.join(RESULT_DIR, "PASS")
SUMMARY_PATH = os.path.join(PASS_DIR, "results_pass.csv")
PSI_PA = 6894.757

# ── 채울 곳 ─────────────────────────────────────────────────
#   형상 이름: {"step": STEP 경로, "power_input_thick": 전원모듈 입구 폭 [mm]}. step 이 None 이면 건너뜀.
CASES = {
    "1pass":      {"step": None, "power_input_thick": 5.0},    # 예: r"E:\...\flowpath_1pass.STEP"
    "1pass_19mm": {"step": None, "power_input_thick": 19.0},   # 1패스는 전원모듈 직렬 → 주 통로와 같은 폭
    "2pass":      {"step": None, "power_input_thick": 5.0},
    "4pass":      {"step": None, "power_input_thick": 5.0},
}

# F5(인자 없이) 실행할 형상 — 비워 두면 STEP 을 채운 CASES 전부
RUN = []

# 차압 대비 온도 이득 표에서 이어 볼 순서 (결과가 있는 것만)
COMPARE = ["1pass", "2pass", "4pass"]
# ───────────────────────────────────────────────────────────


def _check(names):
    for n in names:
        c = CASES[n]
        if c.get("power_input_thick") is None:
            raise ValueError(f"[{n}] power_input_thick(전원모듈 입구 폭)을 채울 것")
        if not c.get("step"):
            raise ValueError(f"[{n}] STEP 경로를 채울 것")
        if not os.path.exists(c["step"]):
            raise FileNotFoundError(f"[{n}] STEP 파일 없음: {c['step']}")


# ── 결과 읽기 ─────────────────────────────────────────────────
def _parse(name, path):
    """행: source01~ N_SOURCE 행 → Fan1_Passage 차압 → Opening1 출구 온도 (icepak.run_icepak measure=False)."""
    cols, col_src = _columns(path)
    df = pd.read_csv(path, header=None, skiprows=SKIP_ROWS, sep=None, engine="python", on_bad_lines="skip")
    names = [str(df.iloc[r, COL_NAME]).strip() for r in range(min(len(df), N_SOURCE + 2))]
    if (len(names) < N_SOURCE + 2 or not all(n.startswith("source") for n in names[:N_SOURCE])
            or names[N_SOURCE] != "Fan1_Passage" or names[N_SOURCE + 1] != "Opening1"):
        raise ValueError(f"[{name}] CSV 행 순서가 예상과 다름 — source {N_SOURCE}행, Fan1_Passage, Opening1 이어야 함: {names}")
    src = range(N_SOURCE)
    s_min = np.array([_num(df.iloc[r, cols["min"]]) for r in src])
    s_max = np.array([_num(df.iloc[r, cols["max"]]) for r in src])
    s_mean = np.array([_num(df.iloc[r, cols["mean"]]) for r in src])
    s_sd = np.array([_num(df.iloc[r, cols["sd"]]) for r in src]) if "sd" in cols else np.full(N_SOURCE, np.nan)
    dp = _num(df.iloc[N_SOURCE, cols["mean"]])
    t_out = _num(df.iloc[N_SOURCE + 1, cols["mean"]])
    if not (np.all(np.isfinite(s_min)) and np.all(np.isfinite(s_max)) and np.all(np.isfinite(s_mean))
            and np.isfinite(dp)):
        raise ValueError(f"[{name}] 발열면 온도 또는 차압이 계산되지 않음(nan)")
    if np.any(s_min > s_mean + 1e-6) or np.any(s_mean > s_max + 1e-6):
        raise ValueError(f"[{name}] 최저 ≤ 평균 ≤ 최고가 아님 — 열 위치({col_src} {cols}) 확인")
    s_range = s_max - s_min
    hb = HEAT_CAPACITY_W_PER_K * (t_out - INLET_TEMP_C) / TOTAL_HEAT_W
    if not np.isfinite(hb) or abs(hb - 1) > HEAT_BALANCE_WARN:
        print(f"  ⚠ [{name}] 열수지 {hb*100:.1f}% (출구 {t_out:.2f} °C) — 팬·오프닝 면이 제대로 잡혔는지 AEDT 화면으로 확인할 것")
    row = {"name": name, "max_temp": float(s_max.max()), "temp_std": float(np.std(s_mean)),
           "temp_in_range": float(s_range.mean()),
           "temp_in_sd": float(s_sd.mean()) if np.all(np.isfinite(s_sd)) else np.nan,
           "temp_in_worst": float(s_range.max()), "hot_slot": int(np.argmax(s_max)) + 1,
           "pressure_drop": float(dp), "pressure_drop_psi": float(dp) / PSI_PA,
           "T_outlet": t_out, "heat_balance": hb, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    for i in src:
        row.update({f"mean_{i + 1:02d}": s_mean[i], f"max_{i + 1:02d}": s_max[i], f"min_{i + 1:02d}": s_min[i]})
    return row


def _save(row):
    old = pd.read_csv(SUMMARY_PATH) if os.path.exists(SUMMARY_PATH) else pd.DataFrame()
    if len(old):
        old = old[old["name"] != row["name"]]          # 같은 형상을 다시 돌리면 덮어씀
    pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(SUMMARY_PATH, index=False)


def report():
    if not os.path.exists(SUMMARY_PATH):
        print("결과가 아직 없습니다.")
        return
    df = pd.read_csv(SUMMARY_PATH)
    cols = ["name", "power_input_thick", "max_temp", "temp_std", "temp_in_range", "temp_in_worst",
            "pressure_drop", "pressure_drop_psi", "heat_balance"]
    print("\n[형상별 결과]")
    print(df[[c for c in cols if c in df.columns]].to_string(index=False, float_format=lambda v: f"{v:.4g}"))

    seq = [n for n in COMPARE if n in set(df["name"])]
    if len(seq) < 2:
        return
    r = df.set_index("name")
    print(f"\n[패스를 늘릴 때 차압 증가 대비 온도 이득] 순서 {' → '.join(seq)}")
    print(f"  {'바꿈':16s} {'차압 증가[psi]':>14s} {'최고온도 감소[°C]':>17s} {'°C/psi':>8s} "
          f"{'채널간 편차 감소':>15s} {'채널안 편차 감소':>15s}")
    for a, b in zip(seq, seq[1:]):
        d_dp = r.loc[b, "pressure_drop_psi"] - r.loc[a, "pressure_drop_psi"]
        d_t = r.loc[a, "max_temp"] - r.loc[b, "max_temp"]
        eff = d_t / d_dp if d_dp > 0 else np.nan
        print(f"  {a + ' → ' + b:16s} {d_dp:14.3f} {d_t:17.2f} {eff:8.2f} "
              f"{r.loc[a, 'temp_std'] - r.loc[b, 'temp_std']:15.3f} "
              f"{r.loc[a, 'temp_in_range'] - r.loc[b, 'temp_in_range']:15.3f}")


def main(names):
    names = names or RUN or [n for n, c in CASES.items() if c.get("step")]
    unknown = [n for n in names if n not in CASES]
    if unknown:
        raise SystemExit(f"해당 형상 없음: {unknown} (가능: {list(CASES)})")
    if not names:
        raise SystemExit("돌릴 형상이 없음 — CASES 의 step 을 채울 것")
    _check(names)
    os.makedirs(PASS_DIR, exist_ok=True)

    desktop, ipk = connect_aedt()
    original = icepak.icepak_result_path
    for k, n in enumerate(names):
        csv_path = os.path.join(PASS_DIR, f"result_pass_{n}.csv")
        print(f"\n===== {n} 해석 시작 ({k + 1}/{len(names)}) {time.strftime('%H:%M:%S')} =====")
        c = CASES[n]
        # run_icepak 은 결과 CSV 경로를 paths.icepak_result_path 로 정한다 — 캠페인 결과와 섞이지 않게 이 동안만 바꿈
        icepak.icepak_result_path = lambda phase, idx: csv_path
        try:
            ipk, path, _ = icepak.run_icepak(desktop, ipk, c["step"], "pass", k,
                                             {"power_input_thick": c["power_input_thick"]}, measure=False)
        finally:
            icepak.icepak_result_path = original
        row = _parse(n, path)
        row["power_input_thick"] = c["power_input_thick"]
        _save(row)
        print(f"[{n}] 최고온도 {row['max_temp']:.2f} °C  채널간 편차 {row['temp_std']:.3f}  "
              f"채널안 편차 {row['temp_in_range']:.3f}  차압 {row['pressure_drop']:.0f} Pa "
              f"({row['pressure_drop_psi']:.3f} psi)  열수지 {row['heat_balance']*100:.1f}%  → {SUMMARY_PATH}")
    report()


if __name__ == "__main__":
    if sys.argv[1:] == ["report"]:
        report()
    else:
        main(sys.argv[1:])
