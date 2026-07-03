import os
import numpy as np
import pandas as pd
from OLHD import generate_olhd

RESULTS_PATH = r"E:\Thermal_Anlaysis\results.csv"
N_DOE        = 20    # 초기 DOE 샘플 수
N_TOTAL      = 40    # 총 실험 횟수 (DOE + GPR)

# DOE 샘플 (고정)
_DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)


def _load_results():
    """results.csv 로드. 없으면 빈 DataFrame 반환."""
    if os.path.exists(RESULTS_PATH):
        return pd.read_csv(RESULTS_PATH)
    return pd.DataFrame(columns=["idx", "angle", "thickness", "max_temp", "temp_std", "pressure_drop"])


def _save_results(df):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


def get_next_params():
    """다음 실험할 (angle, thickness) 반환."""
    df  = _load_results()
    idx = len(df)

    if idx < N_DOE:
        # DOE 단계
        angle     = float(_DOE_SAMPLES[idx, 0])
        thickness = float(_DOE_SAMPLES[idx, 1])
        print(f"[DOE {idx+1}/{N_DOE}] 각도={angle}, 두께={thickness}")
    else:
        # GPR 단계
        angle, thickness = _gpr_suggest(df)
        print(f"[GPR {idx-N_DOE+1}/{N_TOTAL-N_DOE}] 각도={angle}, 두께={thickness}")

    return angle, thickness


def update_ml(angle, thickness, max_temp, temp_std, pressure_drop):
    """해석 결과 저장."""
    df  = _load_results()
    idx = len(df)

    new_row = pd.DataFrame([{
        "idx":           idx,
        "angle":         angle,
        "thickness":     thickness,
        "max_temp":      max_temp,
        "temp_std":      temp_std,
        "pressure_drop": pressure_drop
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save_results(df)
    print(f"[{idx}] 결과 저장 완료")


def is_done():
    """총 N_TOTAL 실험 완료 여부."""
    df = _load_results()
    return len(df) >= N_TOTAL


def _gpr_suggest(df):
    """GPR 기반 다음 실험점 제안 (EI 최대화)."""
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern
    from sklearn.preprocessing import StandardScaler

    X = df[["angle", "thickness"]].values
    # 목적함수: max_temp + temp_std 가중합 (정규화 후)
    y_temp = df["max_temp"].values
    y_std  = df["temp_std"].values
    y_pres = df["pressure_drop"].values

    scaler_y = StandardScaler()
    y = (scaler_y.fit_transform(y_temp.reshape(-1,1)).ravel()
       + scaler_y.fit_transform(y_std.reshape(-1,1)).ravel()
       + scaler_y.fit_transform(y_pres.reshape(-1,1)).ravel())

    scaler_x = StandardScaler()
    X_scaled = scaler_x.fit_transform(X)

    kernel = Matern(nu=2.5)
    gpr    = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, normalize_y=True)
    gpr.fit(X_scaled, y)

    # 후보 격자 탐색
    a_cands = np.arange(0, 31, 1)
    t_cands = np.arange(15, 41, 1)
    grid    = np.array([[a, t] for a in a_cands for t in t_cands])
    grid_scaled = scaler_x.transform(grid)

    mu, sigma = gpr.predict(grid_scaled, return_std=True)

    # EI (Expected Improvement)
    y_best = y.min()
    from scipy.stats import norm
    z  = (y_best - mu) / (sigma + 1e-9)
    ei = (y_best - mu) * norm.cdf(z) + sigma * norm.pdf(z)

    # 이미 실험한 점 제외
    done_set = set(zip(X[:, 0].astype(int), X[:, 1].astype(int)))
    for i, (a, t) in enumerate(grid):
        if (int(a), int(t)) in done_set:
            ei[i] = -1

    best_idx  = np.argmax(ei)
    angle     = float(grid[best_idx, 0])
    thickness = float(grid[best_idx, 1])
    return angle, thickness
