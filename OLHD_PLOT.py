# %%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from OLHD import generate_olhd

# %%
samples = generate_olhd(n_samples=20, seed=42)
angles     = samples[:, 0]
thicknesses = samples[:, 1]

print("OLHD 샘플 (각도, 유로두께):")
for i, (a, t) in enumerate(samples):
    print(f"  {i+1:2d}: 각도={a:5.1f}°  유로두께={t:5.1f}mm")

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Optimal Latin Hypercube Design (20 samples)", fontsize=14, fontweight="bold")

# --- 산점도 ---
ax = axes[0]
sc = ax.scatter(angles, thicknesses, c=range(len(samples)), cmap="tab20", s=100, zorder=3)
for i, (a, t) in enumerate(samples):
    ax.annotate(str(i+1), (a, t), textcoords="offset points", xytext=(6, 4), fontsize=8)

# 격자 (LHS 셀)
n = len(samples)
a_edges = np.linspace(0,  30, n+1)
t_edges = np.linspace(15, 40, n+1)
for ae in a_edges:
    ax.axvline(ae, color="lightgray", linewidth=0.5, zorder=1)
for te in t_edges:
    ax.axhline(te, color="lightgray", linewidth=0.5, zorder=1)

ax.set_xlim(-1, 31)
ax.set_ylim(14, 41)
ax.set_xlabel("각도 (°)", fontsize=11)
ax.set_ylabel("유로두께 (mm)", fontsize=11)
ax.set_title("설계공간 분포")
plt.colorbar(sc, ax=ax, label="샘플 순서")

# --- 1D 마진 히스토그램 ---
ax2 = axes[1]
ax2.hist(angles,      bins=10, alpha=0.6, color="steelblue", label="각도 (°)",      density=True)
ax2.hist(thicknesses, bins=10, alpha=0.6, color="salmon",    label="유로두께 (mm)", density=True)
ax2.set_xlabel("값", fontsize=11)
ax2.set_ylabel("밀도", fontsize=11)
ax2.set_title("각 변수 분포 균일성")
ax2.legend()

plt.tight_layout()
plt.savefig("OLHD_plot.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: OLHD_plot.png")

# %%
# 최소 거리 확인 (공간 균일성 지표)
from scipy.spatial.distance import pdist
dists   = pdist(samples)
print(f"\n최소 샘플 간 거리: {dists.min():.3f}")
print(f"평균 샘플 간 거리: {dists.mean():.3f}")
