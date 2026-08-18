"""
V2 캠페인(results_v2.csv)의 DOE 80개만 V3(results_v3.csv)의 초기 데이터로 이어받는다.

적응샘플링 284개(idx 80~363)는 일부러 제외함 — 그 구간은 옛 목적함수
(max(cv1,cv2))의 불확실성을 따라 골라진 경로라, 새 목적함수(cv1/cv2 분리)
학습의 시드로 쓰면 처음부터 편향을 물려받게 됨. DOE는 목적함수와 무관하게
공간을 고르게 채운 데이터라 어떤 목적함수를 쓰든 유효한 시드임.

한 번만 실행하면 됨 — 이후 main.py가 idx=80부터 새 실험(적응샘플링)을 시작함.
V2가 만든 results_v2.csv / summary_v2.csv / pass_cv_backfill.csv는 읽기만 하고
전혀 수정하지 않음 (results_v3.csv라는 새 파일에만 씀).

전제
  - Result 폴더에 results_v2.csv(기존 캠페인 결과)와
    pass_cv_backfill.csv(backfill_pass_cv.py로 만든 vel_cv_pass1/pass2)가 있어야 함
  - results_v3.csv가 이미 있으면 실수로 덮어쓰지 않도록 중단함
    (다시 시드하고 싶으면 그 파일을 지우거나 백업 후 실행)

사용법
  python seed_from_v2.py
"""
import os
import sys

import pandas as pd

from OLHD import PARAM_NAMES
from paths import RESULTS_PATH, V2_RESULTS_PATH, V2_BACKFILL_CV_PATH
from ML import MODELED_NAMES, N_DOE, _COLUMNS


def main():
    if os.path.exists(RESULTS_PATH):
        print(f"⚠ 이미 {RESULTS_PATH}가 존재합니다 — 실수로 덮어쓰지 않도록 중단합니다.")
        print("  다시 시드하려면 그 파일을 지우거나 다른 이름으로 백업한 뒤 재실행하세요.")
        sys.exit(1)

    if not os.path.exists(V2_RESULTS_PATH):
        print(f"✗ {V2_RESULTS_PATH}가 없습니다 — V2 결과 파일 경로를 확인하세요.")
        sys.exit(1)
    if not os.path.exists(V2_BACKFILL_CV_PATH):
        print(f"✗ {V2_BACKFILL_CV_PATH}가 없습니다 — backfill_pass_cv.py(Code/)를 먼저 실행하세요.")
        sys.exit(1)

    v2 = pd.read_csv(V2_RESULTS_PATH)
    bf = pd.read_csv(V2_BACKFILL_CV_PATH)
    merged = v2.merge(bf[["idx", "vel_cv_pass1", "vel_cv_pass2", "vel_cv_check"]],
                       on="idx", how="left")

    # ── DOE 구간(idx < N_DOE)만 남김 — 적응샘플링 구간은 편향 우려로 제외 ──
    before = len(merged)
    merged = merged[merged["idx"] < N_DOE].copy()
    print(f"DOE 구간만 추림: {before}개 → {len(merged)}개 (idx < {N_DOE})")

    missing_cv = merged["vel_cv_pass1"].isna().sum()
    if missing_cv:
        print(f"⚠ vel_cv_pass1/pass2가 없는 idx {missing_cv}개 — 이 행들은 시드에서 제외합니다.")
        merged = merged.dropna(subset=["vel_cv_pass1", "vel_cv_pass2"])

    if len(merged) != N_DOE:
        print(f"⚠ DOE {N_DOE}개 중 {len(merged)}개만 확보됨 — "
              f"나머지는 V2에서 실패점 처리됐거나 backfill이 안 된 것일 수 있습니다.")

    # vel_cv_check(=max(pass1,pass2))가 기존 vel_cv와 다르면 backfill이 잘못된 것일 수 있음
    mismatch = (merged["vel_cv_check"] - merged["vel_cv"]).abs() > 1e-3
    if mismatch.any():
        print(f"✗ vel_cv 대조검증 불일치 {mismatch.sum()}개 발견 — backfill 파일을 다시 확인하세요.")
        print(merged.loc[mismatch, ["idx", "vel_cv", "vel_cv_check"]].to_string(index=False))
        sys.exit(1)

    # V3 스키마로 필요한 원시값 컬럼만 추림 (pred_*/err_*는 비워둠 — _load_results가 자동 채움)
    seed_cols = ["idx"] + PARAM_NAMES + [
        "pressure_drop", "vel_cv_pass1", "vel_cv_pass2", "temp_std",
        "power_module_flow", "weight",
        "vel_cv", "max_temp",   # 참고용(목적함수 아님) — 있으면 같이 옮겨줌
    ]
    seed_cols = [c for c in seed_cols if c in merged.columns]
    seed = merged[seed_cols].copy().sort_values("idx").reset_index(drop=True)

    missing_needed = [n for n in MODELED_NAMES if n not in seed.columns]
    if missing_needed:
        print(f"✗ V3가 필요로 하는 값이 V2 결과에 없습니다: {missing_needed}")
        sys.exit(1)

    for c in _COLUMNS:
        if c not in seed.columns:
            seed[c] = float("nan")
    seed = seed[[c for c in _COLUMNS if c in seed.columns] +
                [c for c in seed.columns if c not in _COLUMNS]]

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    seed.to_csv(RESULTS_PATH, index=False)

    print(f"✔ 시드 완료: {len(seed)}개 행(DOE만) → {RESULTS_PATH}")
    print(f"  다음 실험은 idx={len(seed)}부터 새로 시작됩니다 (main.py 실행하면 "
          f"곧바로 cv1/cv2 기준 불확실성탐색으로 진입).")
    print(f"  pred_*/err_*는 비어있음 — V3 기준으로는 아직 예측이 없는 게 정상입니다.")


if __name__ == "__main__":
    main()
