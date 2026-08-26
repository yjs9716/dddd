"""
results_v4.csv를 불러와 "완화된 종료기준"으로 다시 판정해서, 실제 모델 구축이
끝난 시점까지만 잘라낸 최종본을 만든다.

배경
  기존 종료기준(모든 objective 상대오차 1% 이하 3회 연속)은 레인 유량(lane1/lane2)에서
  영원히 만족되지 않는다 — 레인 유량은 총유량을 7개로 나눈 값이라 설계가 좋아질수록
  (=레인이 균일해질수록) 상대오차의 분모가 계속 작아져서 상대오차가 구조적으로 못
  내려간다(CV 때와 같은 증폭 문제, 결정계수 자체가 아니라 스케일 문제).

  그래서 판정 기준을 이렇게 바꾼다:
    pressure_drop / temp_std / max_temp : 상대오차 1% 이하 (그대로 — 문제없었음)
    lane_pass1 / lane_pass2             : 절대오차가 총유량의 0.25% 이하
                                           (분모를 "그때그때 예측값"이 아니라
                                            "총유량 4LPM"이라는 고정값으로 바꾼 것뿐,
                                            상대오차 원칙 자체는 유지)
  전 그룹 동시 3회 연속 만족 시점을 "모델 구축 완료"로 보고, 그 이후 데이터는
  실험적으로 더 확보한 여분으로 취급해 잘라낸다.

사용법
  Code3 안에서: python finalize_campaign.py
  results_v4.csv를 읽어서 results_v4_final.csv(잘라낸 것)를 같은 폴더에 만든다.
  원본 results_v4.csv는 건드리지 않는다.
"""
import os
import numpy as np
import pandas as pd

from paths import RESULTS_PATH
from result_parser import LANE1_NAMES, LANE2_NAMES, TOTAL_FLOW_LPM

REL_THRESHOLD = 1.0                       # pressure_drop/temp_std/max_temp 상대오차 기준 [%]
LANE_ABS_THRESHOLD_LPM = TOTAL_FLOW_LPM * 0.25 / 100   # 레인 절대오차 기준 = 총유량의 0.25%
N_CONSECUTIVE = 3

SCALAR_GROUPS = ["pressure_drop", "temp_std", "max_temp"]
LANE_GROUPS = {"lane_pass1": LANE1_NAMES, "lane_pass2": LANE2_NAMES}


def _rel_err(row, name):
    return abs(row.get(f"err_{name}", np.nan))


def _lane_abs_err_max(row, members):
    """레인 그룹의 절대오차(LPM) 중 최댓값 — |예측-실측|을 직접 계산(err_* 열은 %라서 안 씀)."""
    vals = []
    for m in members:
        p, a = row.get(f"pred_{m}"), row.get(m)
        if pd.notna(p) and pd.notna(a):
            vals.append(abs(p - a))
    return max(vals) if vals else np.nan


def evaluate(df):
    """회차별로 새 기준 통과 여부를 판정한 DataFrame 반환."""
    rows = []
    for _, r in df.iterrows():
        d = {"idx": int(r["idx"])}
        ok = True
        for g in SCALAR_GROUPS:
            e = _rel_err(r, g)
            d[f"{g}_rel%"] = e
            ok &= bool(pd.notna(e) and e <= REL_THRESHOLD)
        for g, members in LANE_GROUPS.items():
            e = _lane_abs_err_max(r, members)
            d[f"{g}_abs_LPM"] = e
            ok &= bool(pd.notna(e) and e <= LANE_ABS_THRESHOLD_LPM)
        d["ok"] = ok
        rows.append(d)
    return pd.DataFrame(rows)


def find_termination_idx(eval_df):
    """전 그룹 동시 N_CONSECUTIVE회 연속 만족이 처음 나오는 idx(해당 구간의 마지막 idx) 반환."""
    run = 0
    for i, ok in enumerate(eval_df["ok"]):
        run = run + 1 if ok else 0
        if run >= N_CONSECUTIVE:
            return int(eval_df["idx"].iloc[i])
    return None


def main():
    df = pd.read_csv(RESULTS_PATH)
    adaptive = df.dropna(subset=["pred_pressure_drop"]).sort_values("idx").reset_index(drop=True)

    if len(adaptive) < N_CONSECUTIVE:
        print(f"적응샘플링 데이터가 {len(adaptive)}점뿐 — 판정 불가")
        return

    E = evaluate(adaptive)
    term_idx = find_termination_idx(E)

    if term_idx is None:
        print(f"아직 새 기준(레인 절대오차 ≤ {LANE_ABS_THRESHOLD_LPM:.4f} LPM, "
              f"나머지 상대오차 ≤ {REL_THRESHOLD}%)을 {N_CONSECUTIVE}회 연속 만족한 적 없음.")
        print("최근 10회 판정:")
        print(E.tail(10).to_string(index=False))
        return

    print(f"새 기준 첫 {N_CONSECUTIVE}연속 만족 -> idx {term_idx}에서 모델 구축 완료로 확정")
    print(f"  (레인 절대오차 기준 = 총유량 {TOTAL_FLOW_LPM} LPM의 0.25% = {LANE_ABS_THRESHOLD_LPM:.4f} LPM)\n")

    kept = df[df["idx"] <= term_idx].reset_index(drop=True)
    dropped_n = len(df) - len(kept)

    out_path = os.path.join(os.path.dirname(RESULTS_PATH), "results_v4_final.csv")
    kept.to_csv(out_path, index=False)

    print(f"원본: {len(df)}행 (idx 0~{int(df['idx'].max())})")
    print(f"확정본: {len(kept)}행 (idx 0~{term_idx}) -> {out_path}")
    print(f"제외된 여분 데이터: {dropped_n}행 (idx {term_idx+1}~{int(df['idx'].max())})")


if __name__ == "__main__":
    main()
