"""
기존 results_v5.csv의 err_* 열을 지금 종료기준 방식으로 다시 계산.

배경: err_*는 한동안 "상대오차(%)" 방식으로 기록되다가, 목적함수 5개
(pressure_drop/temp_std/max_temp/std_pass1/std_pass2)에 한해
"|예측-실측| / (ALPHA x S_j)" 방식(1.0이 통과선)으로 바뀌었다(ML.py 참고).
이미 쌓인 데이터는 예전 방식 그대로 남아있으므로, 재실험 없이 이 스크립트로
pred_*/실측값에서 err_*만 다시 뽑아낸다.

제약조건(power_module_flow, weight)은 원래부터 종료판정 대상이 아니라
threshold가 없으므로 그대로 상대오차(%) 방식 유지.

사용법:
    python recompute_err.py                        # paths.RESULTS_PATH 대상
    python recompute_err.py 경로\results_v5.csv      # 특정 파일 대상

안전장치: 덮어쓰기 전 원본을 <파일명>.bak으로 백업.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from ML import N_DOE, ALPHA, OBJ_NAMES, TERMINATION_GROUPS, GROUP_NAMES
from paths import RESULTS_PATH


def recompute(path):
    backup = path + ".bak"
    shutil.copy2(path, backup)
    print(f"[백업] 원본을 {backup}로 복사해둠")

    df = pd.read_csv(path, sep=None, engine="python")
    if "idx" not in df.columns and "dx" in df.columns:
        print("  (참고: 'dx' 열을 'idx'로 정정)")
        df = df.rename(columns={"dx": "idx"})
    if "idx" not in df.columns:
        raise KeyError("idx(또는 dx) 열을 찾을 수 없음 — CSV 헤더 확인 필요")

    doe_rows = df[df["idx"] < N_DOE]
    if len(doe_rows) < N_DOE:
        raise RuntimeError(
            f"DOE {N_DOE}점이 아직 안 채워짐(현재 {len(doe_rows)}점) — "
            "S_j를 계산할 수 없어 재계산 불가"
        )

    S_j = {name: float(doe_rows[name].std(ddof=0)) for name in OBJ_NAMES}
    thr = {g: ALPHA * S_j[spec["members"][0]] for g, spec in TERMINATION_GROUPS.items()}

    print(f"\n[기준] DOE {N_DOE}점 기준 S_j, ALPHA={ALPHA}")
    for g in GROUP_NAMES:
        print(f"    {g:16s} S_j={S_j[g]:.5f}  threshold={thr[g]:.5f}")

    pred_col0 = f"pred_{OBJ_NAMES[0]}"
    if pred_col0 not in df.columns:
        raise KeyError(f"{pred_col0} 열이 없음 — 적응샘플링 데이터가 있는 파일인지 확인")
    adaptive_mask = df[pred_col0].notna()
    print(f"\n적응샘플링(예측값 있는) 행: {adaptive_mask.sum()}개")

    updated = []
    for col in df.columns:
        if not col.startswith("pred_"):
            continue
        base = col[len("pred_"):]
        err_col = f"err_{base}"
        if base not in df.columns or err_col not in df.columns:
            continue

        abs_err = (df.loc[adaptive_mask, col] - df.loc[adaptive_mask, base]).abs()
        if base in TERMINATION_GROUPS:
            df.loc[adaptive_mask, err_col] = abs_err / thr[base]
            mode = f"절대오차/threshold({thr[base]:.5f})"
        else:
            df.loc[adaptive_mask, err_col] = abs_err / df.loc[adaptive_mask, base].abs() * 100
            mode = "상대오차(%)"
        updated.append((err_col, mode))

    df.to_csv(path, index=False)

    print(f"\n[완료] {len(updated)}개 err_* 열, {adaptive_mask.sum()}개 행 갱신:")
    for name, mode in updated:
        print(f"    {name:22s} <- {mode}")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default=RESULTS_PATH,
                    help="대상 CSV 경로 (생략 시 paths.RESULTS_PATH)")
    args = p.parse_args()
    recompute(args.path)
