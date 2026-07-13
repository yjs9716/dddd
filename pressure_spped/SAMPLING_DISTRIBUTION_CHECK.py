# SAMPLING_DISTRIBUTION_CHECK.py
# _gpr_suggest()는 매 회 '정규화 sigma 합이 최대인 점'을 탐욕적으로 고르는 순수 불확실성 탐색이다.
# GP의 예측분산은 구조적으로 설계공간 경계/모서리 근처에서 높게 나오는 경향이 있어,
# 이 방식이 정작 흥미로운 내부 구조(무릎점)보다 경계를 과다 샘플링했을 가능성을 검증한다.
# Jupyter에서 셀 단위로 실행 (results_ps.csv 있는 환경에서)

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.signal import find_peaks

from ML import _fit_models, RESULTS_PATH, _LO, _HI, N_DOE

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

EDGE_MARGIN_RATIO = 0.10   # 경계로부터 이 비율(도메인 폭의 10%) 안쪽을 '경계 근처'로 정의
KNEE_RADIUS_RATIO = 0.10   # 무릎점 근방 판정 반경 (도메인 폭의 10%, 정규화 공간 기준)

df = pd.read_csv(RESULTS_PATH)
print(f"전체 실험 수: {len(df)}  (DOE {N_DOE}개 + 불확실성탐색 {len(df) - N_DOE}개)")


# %%
# ===== 1) 112점(0.3%기준) 모델로 '검증된 무릎점' 위치를 다시 구한다 =====
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
if idx_03 is None:
    raise RuntimeError("0.3% 기준 시점을 찾지 못했습니다.")
df_112 = df.iloc[:idx_03 + 1].reset_index(drop=True)
print(f"0.3%기준 서브셋: {len(df_112)}점 사용")

gpr_dp, gpr_cv = _fit_models(df_112)

grid_step = 0.5
a_cands = np.arange(_LO[0], _HI[0] + 1e-6, grid_step)
t_cands = np.arange(_LO[1], _HI[1] + 1e-6, grid_step)
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
spl = UnivariateSpline(dp_u, cv_u, k=3, s=0.05 * len(dp_u) * cv_u.var())
dp_dense = np.linspace(dp_u.min(), dp_u.max(), 400)
mrs_smooth = -spl.derivative()(dp_dense) * 100

prom = (mrs_smooth.max() - mrs_smooth.min()) * 0.05
peak_idx, _ = find_peaks(mrs_smooth, prominence=prom)
if len(peak_idx) == 0:
    raise RuntimeError("112점 모델에서 검증된 무릎을 못 찾았습니다 (이전 실행과 다른 결과 -> 재확인 필요).")

best_peak_i = peak_idx[np.argmax(mrs_smooth[peak_idx])]
dp_knee = dp_dense[best_peak_i]
nearest_j = int(np.argmin(np.abs(sf[:, 0] - dp_knee)))
knee_angle, knee_thick = sg[nearest_j]
print(f"검증된 무릎점(112점 모델): dp={dp_knee:.1f}Pa, 각도={knee_angle:.1f}°, 두께={knee_thick:.1f}mm")


# %%
# ===== 2) 실제 실험점(185개) 분포 확인: 경계 근처 vs 무릎점 근처 =====
doe_pts = df.iloc[:N_DOE]
adaptive_pts = df.iloc[N_DOE:]   # _gpr_suggest()가 실제로 고른 점들만

a_lo, a_hi = _LO[0], _HI[0]
t_lo, t_hi = _LO[1], _HI[1]
a_margin = (a_hi - a_lo) * EDGE_MARGIN_RATIO
t_margin = (t_hi - t_lo) * EDGE_MARGIN_RATIO


def is_edge(a, t):
    return (a <= a_lo + a_margin) | (a >= a_hi - a_margin) | \
           (t <= t_lo + t_margin) | (t >= t_hi - t_margin)


edge_mask = is_edge(adaptive_pts["angle"].values, adaptive_pts["thickness"].values)
n_adaptive = len(adaptive_pts)
n_edge = int(edge_mask.sum())

# 균일분포라면 경계 밴드 면적비가 곧 기대 비율
area_total = (a_hi - a_lo) * (t_hi - t_lo)
area_edge = area_total - (a_hi - a_lo - 2 * a_margin) * (t_hi - t_lo - 2 * t_margin)
expected_edge_ratio = area_edge / area_total

print(f"\n[불확실성탐색으로 고른 점] 총 {n_adaptive}개")
print(f"  경계 근처(폭 {EDGE_MARGIN_RATIO*100:.0f}% 밴드) 점: {n_edge}개 ({n_edge/n_adaptive*100:.1f}%)")
print(f"  균일분포 기대 비율: {expected_edge_ratio*100:.1f}%  "
      f"-> 실제/기대 = {(n_edge/n_adaptive)/expected_edge_ratio:.2f}배")

# 정규화 공간에서 무릎점 근방 판정
knee_ns = (np.array([knee_angle, knee_thick]) - _LO) / (_HI - _LO)
pts_ns = (adaptive_pts[["angle", "thickness"]].values - _LO) / (_HI - _LO)
dist_to_knee = np.linalg.norm(pts_ns - knee_ns, axis=1)
n_near_knee = int(np.sum(dist_to_knee <= KNEE_RADIUS_RATIO))
area_knee_disk_ratio = np.pi * KNEE_RADIUS_RATIO ** 2  # 정규화 단위원 기준 원 면적비 (근사)
print(f"\n  무릎점 반경 {KNEE_RADIUS_RATIO}(정규화) 이내 점: {n_near_knee}개 ({n_near_knee/n_adaptive*100:.1f}%)")
print(f"  균일분포 기대 비율(근사): {area_knee_disk_ratio*100:.1f}%  "
      f"-> 실제/기대 = {(n_near_knee/n_adaptive)/area_knee_disk_ratio:.2f}배")

if n_near_knee / n_adaptive < area_knee_disk_ratio:
    print("  => 무릎점 근방이 균일분포 기대보다 '적게' 샘플링됨 (과소 샘플링 의심)")
else:
    print("  => 무릎점 근방이 균일분포 기대만큼(또는 그 이상) 샘플링됨")


# %%
fig, ax = plt.subplots(figsize=(8, 7))
ax.scatter(doe_pts["angle"], doe_pts["thickness"], c="lightgray", s=40, marker="s", label=f"DOE 초기 {N_DOE}점")
ax.scatter(adaptive_pts.loc[~edge_mask, "angle"], adaptive_pts.loc[~edge_mask, "thickness"],
           c="tab:blue", s=30, label="불확실성탐색(내부)")
ax.scatter(adaptive_pts.loc[edge_mask, "angle"], adaptive_pts.loc[edge_mask, "thickness"],
           c="tab:red", s=30, label="불확실성탐색(경계 근처)")

# 경계 밴드 표시
from matplotlib.patches import Rectangle
ax.add_patch(Rectangle((a_lo, t_lo), a_hi - a_lo, t_hi - t_lo, fill=False,
                        linestyle="--", edgecolor="gray"))
ax.add_patch(Rectangle((a_lo + a_margin, t_lo + t_margin),
                        (a_hi - a_lo) - 2 * a_margin, (t_hi - t_lo) - 2 * t_margin,
                        fill=False, linestyle=":", edgecolor="tab:red", label="경계밴드 안쪽 경계선"))

circle = plt.Circle((knee_angle, knee_thick), KNEE_RADIUS_RATIO * (a_hi - a_lo),
                     color="gold", fill=False, linewidth=2, label="무릎점 근방(판정반경)")
ax.add_patch(circle)
ax.scatter([knee_angle], [knee_thick], c="gold", s=200, marker="*", edgecolor="black", zorder=10, label="검증된 무릎점")

ax.set_xlabel("각도 (°)")
ax.set_ylabel("유로두께 (mm)")
ax.set_title("실험점 분포: 경계 근처 vs 무릎점 근방")
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
plt.tight_layout()
plt.show()
