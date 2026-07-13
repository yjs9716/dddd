# KNEE_STABILITY_CHECK.py
# 실험 데이터를 "0.5% 3연속 만족 시점 / 0.3% 3연속 만족 시점 / 전체" 3구간으로 잘라
# 각각 GPR을 다시 학습 -> 파레토 프론트 -> 스무딩(스플라인) 후 미분한 한계대체율(MRS)을 겹쳐 그린다.
# 목적: 세 모델의 봉우리 차이가 (A) 진짜 물리적 특징인지 (B) 거친 격자에서의 유한차분 노이즈인지 구분.
# Jupyter에서 셀 단위로 실행 (results_ps.csv 있는 환경에서)

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline

from ML import _fit_models, RESULTS_PATH, _LO, _HI, N_DOE, N_CONSECUTIVE

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

GRID_STEP = 0.5          # 파레토 탐색용 격자 간격 (°, mm) - 1.0보다 세밀, 0.1보다는 O(n^2) 부담 적게
SPLINE_S_FACTOR = 0.05   # 스무딩 강도. 값이 크면 더 매끈해짐 (튜닝 필요할 수 있음)

df_full = pd.read_csv(RESULTS_PATH)
print(f"전체 실험 수: {len(df_full)}")


# %%
def find_stop_index(df, threshold, n_consecutive=N_CONSECUTIVE):
    """이 threshold[%] 기준으로 '3연속 만족'이 최초로 일어나는 시점의 df 행 인덱스(0-base) 반환.
    그 시점까지 실제로 몇 번 실험했는지를 재현하는 것 -> df.iloc[:idx+1] 이 '그때 갖고 있던 데이터'."""
    adaptive = df.dropna(subset=["pred_pressure_drop"]).copy()
    if len(adaptive) < n_consecutive:
        return None

    err_p = (adaptive["pred_pressure_drop"] - adaptive["pressure_drop"]).abs() / adaptive["pressure_drop"].abs() * 100
    err_c = (adaptive["pred_vel_cv"] - adaptive["vel_cv"]).abs() / adaptive["vel_cv"].abs() * 100
    ok = ((err_p <= threshold) & (err_c <= threshold)).to_numpy()
    orig_idx = adaptive.index.to_numpy()   # 원본 df 상의 행 번호

    for i in range(n_consecutive - 1, len(ok)):
        if ok[i - n_consecutive + 1: i + 1].all():
            return int(orig_idx[i])
    return None


idx_05 = find_stop_index(df_full, threshold=0.5)
idx_03 = find_stop_index(df_full, threshold=0.3)

if idx_05 is None or idx_03 is None:
    raise RuntimeError("0.5% 또는 0.3% 기준을 만족하는 시점을 데이터 내에서 찾지 못했습니다. "
                        "results_ps.csv가 전체 캠페인 데이터를 담고 있는지 확인하세요.")

subsets = {
    f"0.5%기준 ({idx_05+1}점)": df_full.iloc[:idx_05 + 1].reset_index(drop=True),
    f"0.3%기준 ({idx_03+1}점)": df_full.iloc[:idx_03 + 1].reset_index(drop=True),
    f"전체 ({len(df_full)}점)": df_full,
}
for name, d in subsets.items():
    print(name, "->", len(d), "개 사용")


# %%
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


def compute_smoothed_mrs(df_subset, grid_step=GRID_STEP, s_factor=SPLINE_S_FACTOR):
    """서브셋 데이터로 GPR 학습 -> 파레토 프론트 -> 스플라인 스무딩 -> 해석적 미분(MRS)."""
    gpr_dp, gpr_cv = _fit_models(df_subset)

    a_cands = np.arange(_LO[0], _HI[0] + 1e-6, grid_step)
    t_cands = np.arange(_LO[1], _HI[1] + 1e-6, grid_step)
    A, T = np.meshgrid(a_cands, t_cands, indexing="ij")
    grid = np.column_stack([A.ravel(), T.ravel()])
    gs = (grid - _LO) / (_HI - _LO)

    mu_p = np.exp(gpr_dp.predict(gs))
    mu_c = gpr_cv.predict(gs)
    F = np.column_stack([mu_p, mu_c])

    mask = pareto_front(F)
    pf = F[mask]
    pg = grid[mask]

    order = np.argsort(pf[:, 0])
    sf = pf[order]
    sg = pg[order]

    # 중복 dp값 제거 (스플라인은 x가 strictly increasing해야 함) -> 같은 dp면 cv 평균
    dp_u, inv = np.unique(sf[:, 0], return_inverse=True)
    cv_u = np.array([sf[inv == i, 1].mean() for i in range(len(dp_u))])

    if len(dp_u) < 4:
        return sf, sg, None, None, None  # 점이 너무 적어 스플라인 불가

    spl = UnivariateSpline(dp_u, cv_u, k=3, s=s_factor * len(dp_u) * cv_u.var())
    dp_dense = np.linspace(dp_u.min(), dp_u.max(), 400)
    cv_smooth = spl(dp_dense)
    mrs_smooth = -spl.derivative()(dp_dense) * 100  # %p / 100Pa 단위 맞추려면 아래서 스케일

    return sf, sg, dp_dense, cv_smooth, mrs_smooth


results = {}
for name, d in subsets.items():
    sf, sg, dp_dense, cv_smooth, mrs_smooth = compute_smoothed_mrs(d)
    results[name] = dict(sf=sf, sg=sg, dp_dense=dp_dense, cv_smooth=cv_smooth, mrs_smooth=mrs_smooth)
    if mrs_smooth is not None:
        peak_i = np.argmax(mrs_smooth)
        print(f"[{name}] 스무딩 후 무릎(최대 MRS) dp={dp_dense[peak_i]:.1f}Pa 부근, "
              f"MRS={mrs_smooth[peak_i]:.4f}")
    else:
        print(f"[{name}] 파레토 점이 너무 적어 스플라인 스무딩 불가")


# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
colors = {name: c for name, c in zip(subsets.keys(), ["tab:blue", "tab:orange", "tab:red"])}

ax1 = axes[0]
for name, r in results.items():
    ax1.plot(r["sf"][:, 0], r["sf"][:, 1], "o", ms=3, alpha=0.3, color=colors[name])
    if r["dp_dense"] is not None:
        ax1.plot(r["dp_dense"], r["cv_smooth"], "-", lw=2, color=colors[name], label=name)
ax1.set_xlabel("차압 (Pa)")
ax1.set_ylabel("속도CV (%)")
ax1.set_title("파레토 프론트: 원본 점(연함) vs 스무딩 곡선")
ax1.legend(fontsize=8)

ax2 = axes[1]
for name, r in results.items():
    if r["dp_dense"] is not None:
        ax2.plot(r["dp_dense"], r["mrs_smooth"], "-", lw=2, color=colors[name], label=name)
        peak_i = np.argmax(r["mrs_smooth"])
        ax2.scatter([r["dp_dense"][peak_i]], [r["mrs_smooth"][peak_i]],
                    color=colors[name], s=100, edgecolor="black", zorder=5)
ax2.set_xlabel("차압 (Pa)")
ax2.set_ylabel("스무딩된 MRS (%p / 100Pa)")
ax2.set_title("스무딩 후 한계대체율 비교 (3개 모델 겹침)")
ax2.legend(fontsize=8)

plt.tight_layout()
plt.show()

print("""
[해석 기준]
- 스무딩 후에도 세 곡선의 봉우리 위치/모양이 비슷하다  -> (A) 실제 물리적 무릎, 격자 노이즈가 아니었음
- 스무딩하면 봉우리가 사라지거나, 스무딩 후에도 세 곡선이 서로 다른 자리에서 봉우리를 만든다
  -> (B) 원래 원시 유한차분(PARETO_PLOT.py의 -d_cv/d_dp) 자체가 격자/모델 노이즈에 민감했던 것.
     이 경우 실험을 더 늘리는 것보다 파레토 프론트를 스무딩해서 쓰는 게 우선입니다.
""")
