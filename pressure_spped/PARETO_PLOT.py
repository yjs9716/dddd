# PARETO_PLOT.py
# 설계공간 전체 격자에 대해 2목적(차압, 속도CV) Pareto 최적점 탐색
# + 무릎점(가중치 기반) + 한계대체율(차압↑ 대비 CV개선 비율) 분석
# Jupyter에서 셀 단위로 실행

# %%
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ML import _fit_models, RESULTS_PATH, _LO, _HI

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# %%
df = pd.read_csv(RESULTS_PATH)
print(f"완료된 실험 수: {len(df)}")

# %%
gpr_dp, gpr_cv = _fit_models(df)

a_cands = np.arange(_LO[0], _HI[0] + 1, 1)
t_cands = np.arange(_LO[1], _HI[1] + 1, 1)
A, T = np.meshgrid(a_cands, t_cands, indexing="ij")
grid = np.column_stack([A.ravel(), T.ravel()])
gs   = (grid - _LO) / (_HI - _LO)

mu_p = np.exp(gpr_dp.predict(gs))
mu_c = gpr_cv.predict(gs)

F = np.column_stack([mu_p, mu_c])   # 전부 최소화 목표 (차압, 속도CV)

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

pareto_mask = pareto_front(F)
pareto_grid = grid[pareto_mask]
pareto_F    = F[pareto_mask]
print(f"Pareto 최적점 수: {pareto_mask.sum()} / {len(F)}")

# %%
# ===== 무릎점(참고용, 가중치 기반) =====
# 정규화된 목적함수 공간에서 이상점(0,0)에 가장 가까운 Pareto점
W = np.array([1.0, 1.0])
f_min = pareto_F.min(axis=0)
f_max = pareto_F.max(axis=0)
F_norm = (pareto_F - f_min) / (f_max - f_min + 1e-12)
knee_idx = np.argmin(np.linalg.norm(F_norm * W, axis=1))
knee_angle, knee_thick = pareto_grid[knee_idx]
knee_dp, knee_cv = pareto_F[knee_idx]
print(f"\n[참고] 가중치 {W} 기준 무릎점: 각도={knee_angle:.0f}°, 두께={knee_thick:.0f}mm"
      f"  (예측차압={knee_dp:.1f}Pa, 예측CV={knee_cv:.2f}%)")

# %%
# ===== 한계대체율 분석 (가중치 없이 직접) =====
# 차압 기준 오름차순 정렬 후, 인접한 두 Pareto점 사이
# "차압 100Pa 더 쓰면 CV가 몇 %p 좋아지는지" 계산 → 비율이 큰 구간이 가성비 구간(무릎)
order = np.argsort(pareto_F[:, 0])
sf = pareto_F[order]     # sorted [dp, cv]
sg = pareto_grid[order]  # sorted [angle, thickness]

ratios = np.full(len(sf), np.nan)
print("\n=== 한계대체율 분석 (차압 증가 대비 CV 개선 비율) ===")
print("각도 | 두께 |  차압  |  CV   | Δ차압 |  ΔCV   | 개선율(%p/100Pa)")
for i in range(len(sf)):
    a, t = sg[i]
    mp, mc = sf[i]
    if i == 0:
        print(f"{a:4.0f} | {t:4.0f} | {mp:6.1f} | {mc:5.2f} |   -   |   -    |    -")
    else:
        d_dp = sf[i, 0] - sf[i-1, 0]     # 이전 대비 차압 증가량 (양수)
        d_cv = sf[i, 1] - sf[i-1, 1]     # 이전 대비 CV 변화량 (프론트 위에서는 음수 = 개선)
        ratio = (-d_cv / d_dp * 100) if d_dp != 0 else float('inf')  # 100Pa당 CV 개선량
        ratios[i] = ratio
        print(f"{a:4.0f} | {t:4.0f} | {mp:6.1f} | {mc:5.2f} | {d_dp:5.1f} | {d_cv:6.3f} | {ratio:8.4f}")

best_seg = np.nanargmax(ratios)
knee2_angle, knee2_thick = sg[best_seg]
knee2_dp, knee2_cv = sf[best_seg]
print(f"\n개선율 최대 구간: 두께 {sg[best_seg-1,1]:.0f}→{sg[best_seg,1]:.0f}mm 부근"
      f"  (100Pa당 CV {ratios[best_seg]:.3f}%p 개선) — 무릎점 후보")
print(f"[참고] 한계대체율 기준 무릎점: 각도={knee2_angle:.0f}°, 두께={knee2_thick:.0f}mm"
      f"  (예측차압={knee2_dp:.1f}Pa, 예측CV={knee2_cv:.2f}%)"
      f"  — 가중치 기준 무릎점과 다른 지점일 수 있음(서로 다른 정의)")

# %%
fig = plt.figure(figsize=(18, 6))

# (1) 목적함수 공간: 차압 vs CV
ax1 = fig.add_subplot(131)
ax1.scatter(F[~pareto_mask, 0], F[~pareto_mask, 1], c="lightgray", s=8, alpha=0.4, label="지배됨")
ax1.plot(sf[:, 0], sf[:, 1], "r.-", linewidth=1, markersize=6, label="Pareto front (차압↑ 순)")
ax1.scatter([knee_dp], [knee_cv], c="gold", s=300, marker="*", edgecolor="black", zorder=10, label="무릎점(가중치)")
ax1.scatter([knee2_dp], [knee2_cv], c="deepskyblue", s=200, marker="D", edgecolor="black", zorder=10, label="무릎점(한계대체율)")
ax1.set_xlabel("차압 (Pa)"); ax1.set_ylabel("속도CV (%)")
ax1.set_title("목적함수 공간 (차압 vs 속도CV)")
ax1.legend(fontsize=8)

# (2) 한계대체율: 프론트 위 구간별 가성비
ax2 = fig.add_subplot(132)
ax2.plot(sf[1:, 0], ratios[1:], "b.-", linewidth=1)
ax2.axvline(knee2_dp, color="deepskyblue", linestyle="--", linewidth=1.5, label="무릎점(한계대체율)")
ax2.axvline(knee_dp, color="gold", linestyle="--", linewidth=1.5, label="무릎점(가중치)")
ax2.set_xlabel("차압 (Pa)"); ax2.set_ylabel("CV 개선율 (%p / 100Pa)")
ax2.set_title("한계대체율 (클수록 가성비 구간)")
ax2.legend(fontsize=8)

# (3) 설계공간 상 위치
ax3 = fig.add_subplot(133)
ax3.scatter(A.ravel(), T.ravel(), c="lightgray", s=5, alpha=0.3, label="전체 격자")
ax3.scatter(pareto_grid[:, 0], pareto_grid[:, 1], c="red", s=40, label="Pareto 최적 설계")
ax3.scatter(df["angle"], df["thickness"], c="black", marker="x", s=30, label="실험점")
ax3.scatter([knee_angle], [knee_thick], c="gold", s=300, marker="*", edgecolor="black", zorder=10, label="무릎점(가중치)")
ax3.scatter([knee2_angle], [knee2_thick], c="deepskyblue", s=200, marker="D", edgecolor="black", zorder=10, label="무릎점(한계대체율)")
ax3.set_xlabel("각도 (°)"); ax3.set_ylabel("유로두께 (mm)")
ax3.set_title("설계공간 상 위치")
ax3.legend(fontsize=8)

plt.tight_layout()
PLOT_DIR = r"E:\Thermal_Anlaysis\260708\plot"
os.makedirs(PLOT_DIR, exist_ok=True)
save_path = os.path.join(PLOT_DIR, "pareto_front_ps.png")
plt.savefig(save_path, dpi=150, bbox_inches="tight")
plt.show()
print(f"저장 완료: {save_path}")
