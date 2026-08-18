"""
5개 목적함수(pressure_drop, vel_cv_pass1, vel_cv_pass2, temp_std, max_temp) 기준으로,
과거 캠페인을 그대로 재현했다면 종료조건(전부 0.5% 이하, 3연속)이 몇 번째 실험에서
달성됐을지 계산한다.

ML.py의 실제 GPR 설정(n_restarts_optimizer=10)을 그대로 써서 정확하게 계산 —
이 세션(외부망)에서는 n_restarts=3으로 근사 계산했었는데, 이 스크립트는 내부망에서
시간에 구애받지 않고 원래 설정 그대로 돌리기 위한 것.

전제
  - results_v2.csv: 기존 캠페인 결과 (X, pressure_drop, temp_std, max_temp,
    그리고 이미 계산된 err_pressure_drop / err_temp_std / err_max_temp 포함)
  - pass_cv_backfill.csv: backfill_pass_cv.py로 만든 idx별 vel_cv_pass1/pass2

방식
  - pressure_drop / temp_std / max_temp는 목적함수 정의가 안 바뀌므로 기존
    err_* 컬럼을 그대로 재사용 (다시 계산할 필요 없음)
  - vel_cv_pass1, vel_cv_pass2만 "그 시점까지의 데이터로 학습했다면 다음 점을
    얼마나 정확히 예측했을까"를 idx마다 처음부터 재현(walk-forward)

사용법
  python replay_5obj_termination.py
  → Result/replay_5obj_result.csv 저장, 콘솔에 최초 3연속 달성 시점(있다면) 출력
"""
import time

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

from OLHD import PARAM_NAMES, LO, HI, N_DIM, DEFAULT_N_DOE
from paths import RESULTS_PATH, RESULT_DIR

BACKFILL_PATH = f"{RESULT_DIR}/pass_cv_backfill.csv"
OUT_PATH = f"{RESULT_DIR}/replay_5obj_result.csv"

ERR_THRESHOLD = 0.5     # ML.py와 동일
N_CONSECUTIVE = 3       # ML.py와 동일
N_RESTARTS = 10         # ML.py의 _fit_gpr와 동일 — 여기서는 줄이지 않음


def normalize(X):
    return (np.asarray(X, dtype=float) - LO) / (HI - LO)


def fit_gpr(Xs, y):
    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * Matern(nu=2.5, length_scale=[0.3] * N_DIM, length_scale_bounds=(0.05, 50.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=N_RESTARTS, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def main():
    df = pd.read_csv(RESULTS_PATH)
    bf = pd.read_csv(BACKFILL_PATH)
    df = df.merge(bf[["idx", "vel_cv_pass1", "vel_cv_pass2"]], on="idx", how="left")
    df = df.sort_values("idx").reset_index(drop=True)

    missing = df["vel_cv_pass1"].isna().sum()
    if missing:
        print(f"⚠ vel_cv_pass1/pass2가 없는 idx {missing}개 — 해당 구간은 건너뜀 "
              f"(backfill_pass_cv.py를 먼저 완전히 돌렸는지 확인)")

    Xs_all = normalize(df[PARAM_NAMES].values)
    cv1_all = df["vel_cv_pass1"].values.astype(float)
    cv2_all = df["vel_cv_pass2"].values.astype(float)

    n_total = len(df)
    n_doe = DEFAULT_N_DOE
    print(f"전체 {n_total}개, DOE {n_doe}개 → 적응샘플링 구간 {n_total - n_doe}개 재현 시작 "
          f"(n_restarts={N_RESTARTS}, 시간 오래 걸릴 수 있음)")

    rows = []
    t_start = time.time()
    for i in range(n_doe, n_total):
        if np.isnan(cv1_all[i]) or np.isnan(cv2_all[i]):
            continue

        Xs_train = Xs_all[:i]
        gpr1 = fit_gpr(Xs_train, cv1_all[:i])
        gpr2 = fit_gpr(Xs_train, cv2_all[:i])

        x_next = Xs_all[i : i + 1]
        pred_cv1 = float(gpr1.predict(x_next)[0])
        pred_cv2 = float(gpr2.predict(x_next)[0])

        err_cv1 = abs(pred_cv1 - cv1_all[i]) / abs(cv1_all[i]) * 100
        err_cv2 = abs(pred_cv2 - cv2_all[i]) / abs(cv2_all[i]) * 100

        rows.append({
            "idx": int(df["idx"].iloc[i]),
            "err_cv1": err_cv1,
            "err_cv2": err_cv2,
            "err_pressure_drop": df["err_pressure_drop"].iloc[i],
            "err_temp_std": df["err_temp_std"].iloc[i],
            "err_max_temp": df["err_max_temp"].iloc[i],
        })

        done = len(rows)
        total = n_total - n_doe
        elapsed = time.time() - t_start
        print(f"[{done}/{total}] idx={df['idx'].iloc[i]}  err_cv1={err_cv1:.3f}%  err_cv2={err_cv2:.3f}%  "
              f"경과 {elapsed:.0f}s  예상총소요 {elapsed/done*total:.0f}s", flush=True)

    out = pd.DataFrame(rows)
    out["row_max_err_5obj"] = out[
        ["err_cv1", "err_cv2", "err_pressure_drop", "err_temp_std", "err_max_temp"]
    ].max(axis=1)
    out.to_csv(OUT_PATH, index=False)
    print(f"\n저장 완료: {OUT_PATH}")

    roll = out["row_max_err_5obj"].rolling(N_CONSECUTIVE).max()
    ok = roll <= ERR_THRESHOLD
    print("\n=== 결과 ===")
    if ok.any():
        first_pos = ok.idxmax()
        window = out.iloc[first_pos - N_CONSECUTIVE + 1 : first_pos + 1]
        end_idx = out["idx"].iloc[first_pos]
        print(f"5개 목적함수 기준, 0.5% 이내 3연속 최초 달성: idx {window['idx'].tolist()} "
              f"(실험 {end_idx}번째에서 종료조건 충족)")
        print(window.to_string(index=False))
    else:
        best_pos = roll.idxmin()
        best_val = roll.min()
        window = out.iloc[best_pos - N_CONSECUTIVE + 1 : best_pos + 1]
        print(f"전체 구간에서 아직 3연속 0.5% 미달성. 가장 좋았던 3연속: "
              f"idx {window['idx'].tolist()}, 필요임계값 {best_val:.3f}%")
        print(window.to_string(index=False))


if __name__ == "__main__":
    main()
