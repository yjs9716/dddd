"""
results_v5.csv를 종료기준으로 다시 판정해서, 모델 구축이 끝난 시점까지만 잘라낸
최종본(results_v5_final.csv)을 만든다. 원본은 건드리지 않는다.

언제 쓰나
  ML.is_done()이 종료를 판정하면 캠페인은 거기서 멈추므로, 정상 흐름에서는 이 스크립트가
  필요 없다. 다음 두 경우에 쓴다:
    · 종료 판정 후에도 실험을 더 돌려 여분 데이터를 쌓았고, 논문/보고서에는
      "모델 구축에 실제로 쓴 데이터"까지만 넣고 싶을 때
    · 기준을 바꿔 재판정하고 싶을 때 (ML.py의 임계값을 바꾸고 다시 돌리면 됨)

판정 기준은 ML.py에서 그대로 가져온다 — 임계값을 두 곳에 적어두면 언젠가 반드시
어긋나므로, 이 파일에는 기준을 다시 쓰지 않는다.

사용법
  260827\\Code 안에서: python finalize_campaign.py
"""
import os

import pandas as pd

from paths import RESULTS_PATH
from ML import (_load_results, _adaptive_rows, _group_values, _group_ok,
                GROUP_NAMES, GROUP_UNIT, TERMINATION_GROUPS, N_CONSECUTIVE,
                REL_THRESHOLD, LANE_ABS_THRESHOLD_LPM)


def evaluate(adaptive):
    """회차별 판정 표 — 그룹별 값과 통과여부, 그리고 전 그룹 동시 통과 여부."""
    gv = _group_values(adaptive)
    ok = _group_ok(adaptive)

    out = pd.DataFrame({"idx": adaptive["idx"].astype(int).values})
    all_ok = None
    for g in GROUP_NAMES:
        out[f"{g}{GROUP_UNIT[g]}"] = gv[g]
        out[f"{g}_ok"] = ok[g]
        all_ok = ok[g] if all_ok is None else (all_ok & ok[g])
    out["ok"] = all_ok
    return out


def find_termination_idx(eval_df):
    """전 그룹 동시 N_CONSECUTIVE회 연속 통과가 처음 나오는 idx(그 구간의 마지막) 반환."""
    run = 0
    for i, ok in enumerate(eval_df["ok"]):
        run = run + 1 if ok else 0
        if run >= N_CONSECUTIVE:
            return int(eval_df["idx"].iloc[i])
    return None


def main():
    df = _load_results()
    if not len(df):
        print(f"결과 파일이 비어 있음: {RESULTS_PATH}")
        return

    adaptive = _adaptive_rows(df).sort_values("idx").reset_index(drop=True)
    if len(adaptive) < N_CONSECUTIVE:
        print(f"적응샘플링 데이터가 {len(adaptive)}점뿐 — 판정 불가")
        return

    print(f"종료기준: 상대오차 <= {REL_THRESHOLD}% "
          f"(pressure_drop/temp_std/max_temp), "
          f"레인 절대오차 <= {LANE_ABS_THRESHOLD_LPM:.4f} LPM, "
          f"{N_CONSECUTIVE}회 연속\n")

    E = evaluate(adaptive)
    term_idx = find_termination_idx(E)

    if term_idx is None:
        print("아직 종료기준을 연속 만족한 적이 없음. 최근 10회 판정:")
        print(E.tail(10).to_string(index=False))
        return

    print(f"첫 {N_CONSECUTIVE}연속 만족 -> idx {term_idx}에서 모델 구축 완료로 확정\n")

    kept = df[df["idx"] <= term_idx].reset_index(drop=True)
    out_path = os.path.join(os.path.dirname(RESULTS_PATH), "results_v5_final.csv")
    kept.to_csv(out_path, index=False)

    print(f"원본  : {len(df)}행 (idx 0~{int(df['idx'].max())})")
    print(f"확정본: {len(kept)}행 (idx 0~{term_idx}) -> {out_path}")
    print(f"제외된 여분 데이터: {len(df) - len(kept)}행")


if __name__ == "__main__":
    main()
