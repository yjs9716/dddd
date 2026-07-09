# 목적함수 = 차압 + 속도CV 2개 (ML_final.py 기반)
# 온도/온도편차는 목적함수에서 제외, 기록용 컬럼으로만 유지
import os
import numpy as np
import pandas as pd
from OLHD import generate_olhd

# 새 캠페인 → 기존 results.csv와 분리 (덮어쓰기 방지)
RESULTS_PATH = r"E:\Thermal_Anlaysis\results_ps.csv"

N_DOE         = 20     # 초기 DOE 샘플 수
ERR_THRESHOLD = 0.5    # 종료 기준: 예측오차 [%] (실측 노이즈 바닥 확인 후 0.5로 확정)
N_CONSECUTIVE = 3      # 연속 만족 횟수 (둘 다 만족해야 종료)

# 설계공간 (OLHD.py와 동일해야 함)
_LO = np.array([0.0,  15.0])   # 각도 min, 두께 min
_HI = np.array([30.0, 40.0])   # 각도 max, 두께 max

# DOE 샘플 (고정 — 기존 캠페인과 동일 seed라 idx별 형상이 같아 직접 비교 가능)
_DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)

_COLUMNS = ["idx", "angle", "thickness",
            "pressure_drop", "vel_cv",             # 목적함수 2개
            "max_temp", "temp_std",                # 기록용 (학습에 안 씀)
            "pred_pressure_drop", "pred_vel_cv"]


def _load_results():
    """results_ps.csv 로드. 없으면 빈 DataFrame."""
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


def update_ml(angle, thickness, pressure_drop, vel_cv, max_temp=np.nan, temp_std=np.nan):
    """해석 결과 저장. 적응 단계면 '실험 전 모델의 예측값'도 같이 기록."""
    df  = _load_results()
    idx = len(df)

    pred_p = pred_c = np.nan
    if idx >= N_DOE:
        # 이번 실험 데이터가 들어가기 전 모델로 예측 → 실측과 비교
        pred_p, pred_c = _predict_point(df, angle, thickness)
        err_p = abs(pred_p - pressure_drop) / abs(pressure_drop) * 100
        err_c = abs(pred_c - vel_cv)        / abs(vel_cv)        * 100
        print(f"[{idx}] 예측오차: 차압 {err_p:.2f}%  속도CV {err_c:.2f}%"
              f"  (종료기준: 둘 다 {ERR_THRESHOLD}% 이하 {N_CONSECUTIVE}회 연속)")

    new_row = pd.DataFrame([{
        "idx":                idx,
        "angle":              angle,
        "thickness":          thickness,
        "pressure_drop":      pressure_drop,
        "vel_cv":             vel_cv,
        "max_temp":           max_temp,
        "temp_std":           temp_std,
        "pred_pressure_drop": pred_p,
        "pred_vel_cv":        pred_c
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save_results(df)
    print(f"[{idx}] 결과 저장 완료")


def is_done():
    """최근 N_CONSECUTIVE회 연속, 두 출력 모두 예측오차 ERR_THRESHOLD% 이하면 종료."""
    df = _load_results()
    adaptive = df.dropna(subset=["pred_pressure_drop"])   # 예측값 있는 행(적응 단계)만
    if len(adaptive) < N_CONSECUTIVE:
        return False

    recent = adaptive.tail(N_CONSECUTIVE)
    err_p = (recent["pred_pressure_drop"] - recent["pressure_drop"]).abs() / recent["pressure_drop"].abs() * 100
    err_c = (recent["pred_vel_cv"]        - recent["vel_cv"]).abs()        / recent["vel_cv"].abs()        * 100

    ok = (err_p <= ERR_THRESHOLD) & (err_c <= ERR_THRESHOLD)
    return bool(ok.all())


# ================== GPR (출력별 2개 분리) ==================
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
    """차압/속도CV 모델 2개 따로 학습."""
    Xs = (df[["angle", "thickness"]].values.astype(float) - _LO) / (_HI - _LO)
    gpr_dp = _fit_gpr(Xs, np.log(df["pressure_drop"].values))   # 차압은 log 변환
    gpr_cv = _fit_gpr(Xs, df["vel_cv"].values)
    return gpr_dp, gpr_cv


def _predict_point(df, angle, thickness):
    """현재까지 데이터로 특정 점의 (차압, 속도CV) 예측."""
    gpr_dp, gpr_cv = _fit_models(df)
    xs = (np.array([[angle, thickness]], dtype=float) - _LO) / (_HI - _LO)
    pred_p = float(np.exp(gpr_dp.predict(xs)[0]))   # log → 원래 단위
    pred_c = float(gpr_cv.predict(xs)[0])
    return pred_p, pred_c


def _gpr_suggest(df):
    """불확실성 우선 탐색: 2개 모델의 정규화 σ 합이 최대인 격자점 제안."""
    gpr_dp, gpr_cv = _fit_models(df)

    # 전체 설계공간 격자 (0.1도/0.1mm, 301x251=75,551점)
    a_cands = np.round(np.arange(0, 30.05, 0.1), 1)
    t_cands = np.round(np.arange(15, 40.05, 0.1), 1)
    grid = np.array([[a, t] for a in a_cands for t in t_cands], dtype=float)
    gs   = (grid - _LO) / (_HI - _LO)

    _, sig_p = gpr_dp.predict(gs, return_std=True)
    _, sig_c = gpr_cv.predict(gs, return_std=True)

    # 정규화 후 합산 → 두 지도가 고르게 정확해지도록
    score = (sig_p / (sig_p.max() + 1e-12)
           + sig_c / (sig_c.max() + 1e-12))

    # 이미 실험한 점 제외 (0.1 단위 → ×10 정수화로 부동소수점 비교 회피)
    done = set(zip((df["angle"] * 10).round().astype(int),
                   (df["thickness"] * 10).round().astype(int)))
    for i, (a, t) in enumerate(grid):
        if (int(round(a * 10)), int(round(t * 10))) in done:
            score[i] = -np.inf

    best_i = int(np.argmax(score))
    return float(grid[best_i, 0]), float(grid[best_i, 1])
