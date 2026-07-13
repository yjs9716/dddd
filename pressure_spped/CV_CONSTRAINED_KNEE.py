# CV_CONSTRAINED_KNEE.py
# CV <= CV_LIMIT 제약 안에서, 그 조건을 만족하는 파레토 구간 중 한계대체율(MRS)이
# 가장 큰 지점을 찾는다. (검증된 112점/0.3%기준 모델 사용)
# 참고: 무제약 MRS 최댓점(dp=1454.9Pa)은 CV=22%라 20% 제약을 위반하므로,
#       제약 하에서는 그 지점을 못 쓰고 '실현 가능한 영역 안에서 최선'을 찾아야 한다.
# Jupyter에서 셀 단위로 실행 (results_ps.csv 있는 환경에서)

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.signal import find_peaks

from ML import _fit_models, RESULTS_PATH, _LO, _HI

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

CV_LIMIT = 20.0     # CV 상한 제약 (%)
GRID_STEP = 0.5
SPLINE_S_FACTOR = 0.05

df = pd.read_csv(RESULTS_PATH)


def find_stop_index(df, threshold, n_consecutive=3):
    adaptive = df.dropna(subset=["pred_pressure_drop"]).copy()
    if len(adaptive) < n_consecutive:
        return None
    err_p = (adaptive["pred_pressure_drop"] - adaptive["pressure_drop"]).abs() / adaptive["pressure_drop"].abs() * 100
    err_c = (adaptive["pred_vel_cv"] - adaptive["vel_cv"]).abs() / adaptive["vel_cv"].abs() * 100
    ok = ((err_p <= threshold) & (err_c <= threshold)).to_numpy()
    orig_idx = adaptive.index.to_numpy()
    for i in range(n_consecutive - 1, len(ok)):
        if ok[i - n_consecutive + 1: i + 1].all():
            return int(orig_idx[i])
    return None


def pareto_front(F):
    n = F.shape[0]
    is_pareto = np.ones(n, dtype=bool)
    for i in range(n):
        if not is_pareto[i]:
            continue
        dominates = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        if np.any(dominates):
            is_pareto[i] = False
    return is_pareto


idx_03 = find_stop_index(df, threshold=0.3)
df_112 = df.iloc[:idx_03 + 1].reset_index(drop=True)
print(f"0.3%기준(검증된) 서브셋: {len(df_112)}점 사용, CV 상한 제약: {CV_LIMIT}%")

gpr_dp, gpr_cv = _fit_models(df_112)

a_cands = np.arange(_LO[0], _HI[0] + 1e-6, GRID_STEP)
t_cands = np.arange(_LO[1], _HI[1] + 1e-6, GRID_STEP)
A, T = np.meshgrid(a_cands, t_cands, indexing="ij")
grid = np.column_stack([A.ravel(), T.ravel()])
gs = (grid - _LO) / (_HI - _LO)

mu_p = np.exp(gpr_dp.predict(gs))
mu_c = gpr_cv.predict(gs)
F = np.column_stack([mu_p, mu_c])
mask = pareto_front(F)
pf, pg = F[mask], grid[mask]
order = np.argsort(pf[:, 0])
sf, sg = pf[order], pg[order]

dp_u, inv = np.unique(sf[:, 0], return_inverse=True)
cv_u = np.array([sf[inv == i, 1].mean() for i in range(len(dp_u))])
spl = UnivariateSpline(dp_u, cv_u, k=3, s=SPLINE_S_FACTOR * len(dp_u) * cv_u.var())
dp_dense = np.linspace(dp_u.min(), dp_u.max(), 800)
cv_smooth = spl(dp_dense)
mrs_smooth = -spl.derivative()(dp_dense) * 100

# %%
feasible = cv_smooth <= CV_LIMIT
if not feasible.any():
    raise RuntimeError(f"CV<={CV_LIMIT}%를 만족하는 파레토 구간이 없습니다. 상한을 높이세요.")

# 제약 경계(cv가 정확히 CV_LIMIT을 넘는 지점) 파악
dp_boundary = np.interp(CV_LIMIT, cv_smooth[::-1], dp_dense[::-1])  # cv_smooth는 dp에 대해 감소함수라 뒤집어서 보간

best_i_feasible = np.argmax(mrs_smooth[feasible])
best_i = np.where(feasible)[0][best_i_feasible]
dp_best, cv_best, mrs_best = dp_dense[best_i], cv_smooth[best_i], mrs_smooth[best_i]

is_at_boundary = abs(dp_best - dp_boundary) < (dp_dense[1] - dp_dense[0]) * 3
print(f"\nCV<={CV_LIMIT}% 제약을 만족하는 dp 시작점: {dp_boundary:.1f}Pa (여기서 CV={CV_LIMIT}%)")
print(f"제약 안에서 MRS 최대점: dp={dp_best:.1f}Pa, CV={cv_best:.2f}%, MRS={mrs_best:.4f}")
if is_at_boundary:
    print("=> 제약 경계(CV=20% 바로 그 지점)에서 MRS가 최대. "
          "즉 무제약 MRS 피크(CV22%)는 못 쓰니, '허용 범위 안에서 가장 CV를 낮춘 지점 바로 그 자체'가 최선입니다.")
else:
    print("=> 제약 안쪽(경계보다 더 CV를 낮춘 곳)에 진짜 국소 최댓값이 있습니다.")

nearest_j = int(np.argmin(np.abs(sf[:, 0] - dp_best)))
best_angle, best_thick = sg[nearest_j]
print(f"해당 설계점: 각도={best_angle:.1f}°, 두께={best_thick:.1f}mm")

# %%
# 근처 실측점 확인 (모델 예측이 아니라 실제로 검증되는 값인지)
near = df_112.iloc[(df_112["pressure_drop"] - dp_best).abs().argsort()[:5]]
print(f"\ndp={dp_best:.1f}Pa 근방 실측점 5개:")
print(near[["idx", "angle", "thickness", "pressure_drop", "vel_cv"]].to_string(index=False))

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].plot(sf[:, 0], sf[:, 1], "o", ms=3, alpha=0.3, color="gray", label="원본 파레토점")
axes[0].plot(dp_dense, cv_smooth, "b-", lw=2, label="스무딩 프론트")
axes[0].axhline(CV_LIMIT, color="tab:red", linestyle="--", label=f"CV={CV_LIMIT}% 제약선")
axes[0].scatter([dp_best], [cv_best], c="gold", s=200, marker="*", edgecolor="black", zorder=10, label="제약 하 최적점")
axes[0].set_xlabel("차압 (Pa)"); axes[0].set_ylabel("속도 CV (%)")
axes[0].set_title("파레토 프론트 + CV 제약")
axes[0].legend(fontsize=8)

axes[1].plot(dp_dense, mrs_smooth, "b-", lw=1, alpha=0.4, label="MRS (전체)")
axes[1].plot(dp_dense[feasible], mrs_smooth[feasible], "b-", lw=2, label=f"MRS (CV≤{CV_LIMIT}% 실현가능)")
axes[1].axvline(dp_boundary, color="tab:red", linestyle="--", label="제약 경계")
axes[1].scatter([dp_best], [mrs_best], c="gold", s=200, marker="*", edgecolor="black", zorder=10, label="제약 하 최적점")
axes[1].set_xlabel("차압 (Pa)"); axes[1].set_ylabel("MRS (%p/100Pa)")
axes[1].set_title("한계대체율 + 실현가능영역")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.show()
