"""
DOE + 제약조건 베이지안 최적화

정식화:
    minimize   pressure_drop            (고정유량 해석에서 차압↓ = 실환경 유량↑ = 온도↓)
    subject to max_temp  <= T_MAX_LIMIT
               temp_std  <= T_STD_LIMIT

흐름:
    idx 0 ~ N_DOE-1   : OLHD 초기 실험 (설계공간 균등 탐색)
    idx N_DOE ~       : GPR 3개(온도/편차/log차압) + Constrained EI로 다음 점 제안
    results.csv 로 진행상태 영속화 → 중단 후 재실행하면 이어서 진행
"""
import os
import numpy as np
import pandas as pd
from OLHD import generate_olhd, ANGLE_MIN, ANGLE_MAX, THICK_MIN, THICK_MAX

# ================== 설정 ==================
RESULTS_PATH = r"E:\Thermal_Anlaysis\results.csv"

N_DOE   = 20    # 초기 DOE 샘플 수
N_TOTAL = 30    # 총 실험 횟수 (DOE + 적응 샘플링)

# 제약조건 상한 -- TODO: 실제 스펙 값으로 수정할 것!
T_MAX_LIMIT = 85.0   # 최대온도 상한 [degC]
T_STD_LIMIT = 5.0    # 온도 표준편차 상한 [degC]

# DOE 샘플 (seed 고정 → 매 실행 동일)
_DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)


# ================== 진행상태 관리 ==================
def _load_results():
    if os.path.exists(RESULTS_PATH):
        return pd.read_csv(RESULTS_PATH)
    return pd.DataFrame(columns=["idx", "angle", "thickness", "max_temp", "temp_std", "pressure_drop"])


def _save_results(df):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


def get_next_params():
    """다음 실험할 (idx, angle, thickness) 반환."""
    df  = _load_results()
    idx = len(df)

    if idx < N_DOE:
        angle, thickness = _DOE_SAMPLES[idx]
        print(f"[DOE {idx+1}/{N_DOE}] 각도={angle}, 두께={thickness}")
    else:
        angle, thickness = _suggest_next(df)
        print(f"[적응샘플링 {idx-N_DOE+1}/{N_TOTAL-N_DOE}] 각도={angle}, 두께={thickness}")

    return idx, float(angle), float(thickness)


def update_ml(idx, angle, thickness, max_temp, temp_std, pressure_drop):
    """해석 결과 한 줄 저장."""
    df = _load_results()
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
    return len(_load_results()) >= N_TOTAL


# ================== GPR 모델 ==================
def _scale(X):
    """설계공간 → [0,1] 스케일 (결정론적, 데이터 무관)"""
    lo = np.array([ANGLE_MIN, THICK_MIN], dtype=float)
    hi = np.array([ANGLE_MAX, THICK_MAX], dtype=float)
    return (np.asarray(X, dtype=float) - lo) / (hi - lo)


def _fit_gpr(Xs, y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * Matern(nu=2.5, length_scale=[0.3, 0.3], length_scale_bounds=(0.05, 5.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))  # CFD 수렴 노이즈 흡수
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def fit_models(df):
    """출력별 GPR 3개 fitting. (RESPONSE_PLOT.py에서도 사용)"""
    Xs = _scale(df[["angle", "thickness"]].values)
    gpr_temp = _fit_gpr(Xs, df["max_temp"].values)
    gpr_std  = _fit_gpr(Xs, df["temp_std"].values)
    gpr_ldp  = _fit_gpr(Xs, np.log(df["pressure_drop"].values))  # 차압은 log 변환
    return gpr_temp, gpr_std, gpr_ldp


def make_grid():
    """전체 설계공간 격자 (1mm/1deg 간격). (RESPONSE_PLOT.py에서도 사용)"""
    a = np.arange(ANGLE_MIN, ANGLE_MAX + 1, 1)
    t = np.arange(THICK_MIN, THICK_MAX + 1, 1)
    A, T = np.meshgrid(a, t, indexing="ij")
    grid = np.column_stack([A.ravel(), T.ravel()]).astype(float)
    return grid, A, T


def predict_grid(df):
    """격자 전체에 대한 예측 평균/표준편차. (RESPONSE_PLOT.py에서도 사용)"""
    gpr_temp, gpr_std, gpr_ldp = fit_models(df)
    grid, A, T = make_grid()
    gs = _scale(grid)

    mu_t, sig_t = gpr_temp.predict(gs, return_std=True)
    mu_s, sig_s = gpr_std.predict(gs, return_std=True)
    mu_l, sig_l = gpr_ldp.predict(gs, return_std=True)

    return grid, A, T, (mu_t, sig_t), (mu_s, sig_s), (mu_l, sig_l)


# ================== 적응 샘플링 (Constrained EI) ==================
def _suggest_next(df):
    from scipy.stats import norm

    grid, A, T, (mu_t, sig_t), (mu_s, sig_s), (mu_l, sig_l) = predict_grid(df)

    # 제약 만족 확률: P(temp<=상한) * P(std<=상한)
    pf_t = norm.cdf((T_MAX_LIMIT - mu_t) / (sig_t + 1e-9))
    pf_s = norm.cdf((T_STD_LIMIT - mu_s) / (sig_s + 1e-9))
    pf   = pf_t * pf_s

    # 현재까지 제약 만족 실측점 중 최소 log차압 (없으면 전체 최소)
    feas = (df["max_temp"] <= T_MAX_LIMIT) & (df["temp_std"] <= T_STD_LIMIT)
    if feas.any():
        best = np.log(df.loc[feas, "pressure_drop"].min())
    else:
        best = np.log(df["pressure_drop"].min())

    # EI on log(pressure_drop)
    z  = (best - mu_l) / (sig_l + 1e-9)
    ei = (best - mu_l) * norm.cdf(z) + sig_l * norm.pdf(z)

    # Constrained EI = EI * 제약만족확률
    cei = ei * pf

    # 이미 실험한 점 제외
    done = set(zip(df["angle"].round().astype(int), df["thickness"].round().astype(int)))
    for i, (a, t) in enumerate(grid):
        if (int(a), int(t)) in done:
            cei[i] = -np.inf

    # CEI가 전부 0이면(제약 못 찾거나 수렴) 탐색 모드: 불확실성 큰 곳
    if not np.isfinite(cei.max()) or cei.max() <= 0:
        fallback = sig_l * pf
        for i, (a, t) in enumerate(grid):
            if (int(a), int(t)) in done:
                fallback[i] = -np.inf
        best_i = int(np.argmax(fallback))
    else:
        best_i = int(np.argmax(cei))

    return grid[best_i, 0], grid[best_i, 1]
