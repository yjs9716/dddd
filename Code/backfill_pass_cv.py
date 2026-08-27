"""
과거 캠페인의 개별 Icepak 결과 CSV(result_000.csv ~ result_XXX.csv)를 다시 읽어
1차/2차 통과 CV(vel_cv_pass1, vel_cv_pass2)를 복원한다.

배경
  summary_v2.csv에 vel_cv_pass1/pass2가 없거나 유실된 경우(요약본 손상 시 재시작되는
  로직이 result_parser.py에 있음 — 원시 vel_cv는 results_v2.csv에 남지만 통과별 분해값은
  요약본에만 있었음), 이 값을 다시 얻으려면 새 해석을 돌릴 필요 없이 이미 저장된
  ICEPAK_RESULT_DIR의 원본 CSV에서 다시 계산하면 된다 — result_parser._lane_flow_cv()와
  완전히 동일한 로직을 재사용.

사용법
  python backfill_pass_cv.py
  → RESULT_DIR에 pass_cv_backfill.csv 생성 (idx, vel_cv_pass1, vel_cv_pass2, vel_cv_check)
    vel_cv_check = max(pass1, pass2) — 기존 results_v2.csv의 vel_cv와 대조 검증용
"""
import os

import pandas as pd

from paths import ICEPAK_RESULT_DIR, RESULT_DIR, RESULTS_PATH
from result_parser import ROW_LANE1, ROW_LANE2, N_ROWS, _lane_flow_cv

OUT_PATH = os.path.join(RESULT_DIR, "pass_cv_backfill.csv")


def _read_result_csv(path):
    return pd.read_csv(path, header=None, skiprows=5, sep=None, engine="python",
                        on_bad_lines="skip")


def backfill():
    # results_v2.csv에 있는 idx만큼만 시도 (실패점은 애초에 result_XXX.csv가 없음)
    known = pd.read_csv(RESULTS_PATH)
    idxs = sorted(known["idx"].astype(int).tolist())

    rows, missing, bad = [], [], []
    for idx in idxs:
        path = os.path.join(ICEPAK_RESULT_DIR, f"result_{idx:03d}.csv")
        if not os.path.exists(path):
            missing.append(idx)
            continue
        try:
            df = _read_result_csv(path)
            if len(df) < N_ROWS:
                bad.append((idx, f"행 {len(df)}개뿐 (기대 {N_ROWS})"))
                continue
            cv1 = _lane_flow_cv(df, ROW_LANE1)
            cv2 = _lane_flow_cv(df, ROW_LANE2)
            rows.append({"idx": idx, "vel_cv_pass1": cv1, "vel_cv_pass2": cv2,
                         "vel_cv_check": max(cv1, cv2)})
        except Exception as e:
            bad.append((idx, str(e)))

    out = pd.DataFrame(rows).sort_values("idx")
    out.to_csv(OUT_PATH, index=False)

    print(f"복원 완료: {len(out)} / {len(idxs)}개")
    print(f"저장 위치: {OUT_PATH}")
    if missing:
        print(f"⚠ 원본 CSV 없음 ({len(missing)}개): {missing[:20]}{' ...' if len(missing) > 20 else ''}")
    if bad:
        print(f"⚠ 파싱 실패 ({len(bad)}개):")
        for idx, reason in bad[:20]:
            print(f"   idx {idx}: {reason}")

    # 기존 results_v2.csv의 vel_cv와 교차검증 (같아야 정상)
    merged = out.merge(known[["idx", "vel_cv"]], on="idx", how="left")
    diff = (merged["vel_cv_check"] - merged["vel_cv"]).abs()
    mismatch = merged[diff > 1e-6]
    if len(mismatch):
        print(f"\n⚠ 기존 vel_cv와 불일치하는 idx {len(mismatch)}개 — 원본 CSV가 그 사이 바뀌었을 가능성:")
        print(mismatch[["idx", "vel_cv", "vel_cv_check"]].to_string(index=False))
    else:
        print("\n✔ 전체 idx에서 max(pass1, pass2)가 기존 results_v2.csv의 vel_cv와 일치")


if __name__ == "__main__":
    backfill()
