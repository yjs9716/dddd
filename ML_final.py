import os
import numpy as np
import pandas as pd
from OLHD import generate_olhd

RESULTS_PATH = r"E:\Thermal_Anlaysis\results.csv"

N_DOE         = 20     # 초기 DOE 샘플 수
ERR_THRESHOLD = 1.0    # 종료 기준: 예측오차 [%]
N_CONSECUTIVE = 3      # 연속 만족 횟수 (전부 만족해야 종료)

# 설계공간 (OLHD.py와 동일해야 함)
_LO = np.array([0.0,  15.0])   # 각도 min, 두께 min
_HI = np.array([30.0, 40.0])   # 각도 max, 두께 max

# DOE 샘플 (고정)
_DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)

_COLUMNS = ["idx", "angle", "thickness",
            "max_temp", "temp_std", "pressure_drop",
            "pred_max_temp", "pred_temp_std", "pred_pressure_drop"]


def _load_results():
    """results.csv 로드. 없으면 빈 DataFrame. (구버전 파일이면 pred 컬럼 NaN으로 추가)"""
    if os.path.exists(RESULTS_PATH):
        df = pd.read_csv(RESULTS_PATH)
        for c in _COLUMNS:
            if c not in df.columns:
                df[c] = np.nan
        return df
    return pd.DataFrame(columns=_COLUMNS)


def _save_results(df):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


def get_next_params():
    """다음 실험할 (angle, thickness) 반환."""
    df  = _load_results()
    idx = len(df)

    if idx < N_DOE:
        angle     = float(_DOE_SAMPLES[idx, 0])
        thickness = float(_DOE_SAMPLES[idx, 1])
        print(f"[DOE {idx+1}/{N_DOE}] 각도={angle}, 두께={thickness}")
    else:
        angle, thickness = _gpr_suggest(df)
        print(f"[불확실성탐색 {idx-N_DOE+1}회차] 각도={angle}, 두께={thickness}")

    return angle, thickness


def update_ml(angle, thickness, max_temp, temp_std, pressure_drop):
    """해석 결과 저장. 적응 단계면 '실험 전 모델의 예측값'도 같이 기록."""
    df  = _load_results()
    idx = len(df)

    pred_t = pred_s = pred_p = np.nan
    if idx >= N_DOE:
        # 이번 실험 데이터가 들어가기 전 모델로 예측 → 실측과 비교
        pred_t, pred_s, pred_p = _predict_point(df, angle, thickness)
        err_t = abs(pred_t - max_temp)      / abs(max_temp)      * 100
        err_s = abs(pred_s - temp_std)      / abs(temp_std)      * 100
        err_p = abs(pred_p - pressure_drop) / abs(pressure_drop) * 100
        print(f"[{idx}] 예측오차: 온도 {err_t:.2f}%  편차 {err_s:.2f}%  차압 {err_p:.2f}%"
              f"  (종료기준: 셋 다 {ERR_THRESHOLD}% 이하 {N_CONSECUTIVE}회 연속)")

    new_row = pd.DataFrame([{
        "idx":                idx,
        "angle":              angle,
        "thickness":          thickness,
        "max_temp":           max_temp,
        "temp_std":           temp_std,
        "pressure_drop":      pressure_drop,
        "pred_max_temp":      pred_t,
        "pred_temp_std":      pred_s,
        "pred_pressure_drop": pred_p
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save_results(df)
    print(f"[{idx}] 결과 저장 완료")


def is_done():
    """최근 N_CONSECUTIVE회 연속, 세 출력 모두 예측오차 ERR_THRESHOLD% 이하면 종료."""
    df = _load_results()
    adaptive = df.dropna(subset=["pred_max_temp"])   # 예측값 있는 행(적응 단계)만
    if len(adaptive) < N_CONSECUTIVE:
        return False

    recent = adaptive.tail(N_CONSECUTIVE)
    err_t = (recent["pred_max_temp"]      - recent["max_temp"]).abs()      / recent["max_temp"].abs()      * 100
    err_s = (recent["pred_temp_std"]      - recent["temp_std"]).abs()      / recent["temp_std"].abs()      * 100
    err_p = (recent["pred_pressure_drop"] - recent["pressure_drop"]).abs() / recent["pressure_drop"].abs() * 100

    ok = (err_t <= ERR_THRESHOLD) & (err_s <= ERR_THRESHOLD) & (err_p <= ERR_THRESHOLD)
    return bool(ok.all())


# ================== GPR (출력별 3개 분리) ==================
def _fit_gpr(Xs, y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * Matern(nu=2.5, length_scale=[0.3, 0.3], length_scale_bounds=(0.05, 5.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))  # CFD 노이즈 흡수
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def _fit_models(df):
    """온도/편차/차압 모델 3개 따로 학습."""
    Xs = (df[["angle", "thickness"]].values.astype(float) - _LO) / (_HI - _LO)
    gpr_temp = _fit_gpr(Xs, df["max_temp"].values)
    gpr_std  = _fit_gpr(Xs, df["temp_std"].values)
    gpr_dp   = _fit_gpr(Xs, np.log(df["pressure_drop"].values))   # 차압은 log 변환
    return gpr_temp, gpr_std, gpr_dp


def _predict_point(df, angle, thickness):
    """현재까지 데이터로 특정 점의 (온도, 편차, 차압) 예측."""
    gpr_temp, gpr_std, gpr_dp = _fit_models(df)
    xs = (np.array([[angle, thickness]], dtype=float) - _LO) / (_HI - _LO)
    pred_t = float(gpr_temp.predict(xs)[0])
    pred_s = float(gpr_std.predict(xs)[0])
    pred_p = float(np.exp(gpr_dp.predict(xs)[0]))   # log → 원래 단위
    return pred_t, pred_s, pred_p


def _gpr_suggest(df):
    """불확실성 우선 탐색: 3개 모델의 정규화 σ 합이 최대인 점 제안."""
    gpr_temp, gpr_std, gpr_dp = _fit_models(df)

    # 전체 설계공간 격자 (1도/1mm, 31x26=806점)
    a_cands = np.arange(0, 31, 1)
    t_cands = np.arange(15, 41, 1)
    grid = np.array([[a, t] for a in a_cands for t in t_cands], dtype=float)
    gs   = (grid - _LO) / (_HI - _LO)

    _, sig_t = gpr_temp.predict(gs, return_std=True)
    _, sig_s = gpr_std.predict(gs, return_std=True)
    _, sig_p = gpr_dp.predict(gs, return_std=True)

    # 정규화 후 합산 → 세 지도가 고르게 정확해지도록
    score = (sig_t / (sig_t.max() + 1e-12)
           + sig_s / (sig_s.max() + 1e-12)
           + sig_p / (sig_p.max() + 1e-12))

    # 이미 실험한 점 제외
    done = set(zip(df["angle"].round().astype(int), df["thickness"].round().astype(int)))
    for i, (a, t) in enumerate(grid):
        if (int(a), int(t)) in done:
            score[i] = -np.inf

    best_i = int(np.argmax(score))
    return float(grid[best_i, 0]), float(grid[best_i, 1])
