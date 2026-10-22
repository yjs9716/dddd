# %%
"""
OLHD 샘플 분포 시각화 — 변수 개수(N_DIM)와 무관하게 동작

  - 변수가 여럿(mm/deg/개수 혼재)이라 2D 산점도 하나로 설계공간을 못 보여줌
    → 변수쌍 전체(하삼각 산점도, N_DIM x N_DIM)로 확장
  - 최소/평균 거리도 정규화 공간([0,1]^N_DIM) 기준으로 계산
    → mm(15~40)와 deg(90~150)처럼 스케일이 다른 변수가 섞여있어,
      원래 값 그대로 거리를 재면 범위 넓은 변수(각도)가 지배해버림
  - OLHD.PARAM_SPEC/FIXED_PARAMS를 그대로 import해서 쓰므로, 변수 구성이
    바뀌어도(V5: 9변수 + fin_height/power_output_thick 고정) 이 파일은 안 고쳐도 됨
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist

from OLHD import generate_olhd, PARAM_NAMES, N_DIM, LO, HI

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# %%
samples = generate_olhd(seed=42)   # 기본 DEFAULT_N_DOE(=10 x N_DIM)개
n = len(samples)

print(f"OLHD 샘플 {n}개 ({N_DIM}변수)")
print("  " + "  ".join(f"{name:>18s}" for name in PARAM_NAMES))
for i, row in enumerate(samples):
    print(f"{i+1:3d}: " + "  ".join(f"{v:18.1f}" for v in row))

# %%
# --- 변수별 분포 균일성 (marginal histogram) ---
n_cols = 4
n_rows = int(np.ceil(N_DIM / n_cols))
fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3.2 * n_rows))
fig.suptitle(f"변수별 분포 균일성 (OLHD {n}점, {N_DIM}변수)", fontsize=14, fontweight="bold")
axes = np.array(axes).reshape(-1)

for i, name in enumerate(PARAM_NAMES):
    ax = axes[i]
    ax.hist(samples[:, i], bins=10, color="steelblue", edgecolor="white")
    ax.set_title(name, fontsize=10)
    ax.set_xlabel("값", fontsize=9)
    ax.set_ylabel("빈도", fontsize=9)
    ax.set_xlim(LO[i], HI[i])

for j in range(N_DIM, len(axes)):
    axes[j].axis("off")

plt.tight_layout()
plt.savefig("OLHD_marginal.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: OLHD_marginal.png")

# %%
# --- 변수쌍 산점도 (하삼각) — 설계공간 커버리지 확인용 ---
#   대각선: 각 변수의 분포(marginal histogram, 위와 동일한 정보를 여기서도 확인 가능)
#   하삼각: 두 변수 조합에서 점이 고르게 퍼져 있는지 (특정 구석에 몰려있으면 안 됨)
fig2, axes2 = plt.subplots(N_DIM, N_DIM, figsize=(2.2 * N_DIM, 2.2 * N_DIM))
fig2.suptitle(f"변수쌍 산점도 (설계공간 커버리지, {n}점)", fontsize=14, fontweight="bold")

for i in range(N_DIM):
    for j in range(N_DIM):
        ax = axes2[i, j]
        if i == j:
            ax.hist(samples[:, i], bins=10, color="salmon", edgecolor="white")
        elif i > j:
            ax.scatter(samples[:, j], samples[:, i], s=12, color="steelblue", alpha=0.7)
            ax.set_xlim(LO[j], HI[j])
            ax.set_ylim(LO[i], HI[i])
        else:
            ax.axis("off")
            continue

        if i == N_DIM - 1:
            ax.set_xlabel(PARAM_NAMES[j], fontsize=7)
        else:
            ax.set_xticklabels([])
        if j == 0:
            ax.set_ylabel(PARAM_NAMES[i], fontsize=7)
        else:
            ax.set_yticklabels([])
        ax.tick_params(labelsize=6)

plt.tight_layout()
plt.savefig("OLHD_pairwise.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: OLHD_pairwise.png")

# %%
# --- 최소/평균 거리 (공간 균일성 지표) ---
#   정규화 공간([0,1]^N_DIM) 기준: mm/deg처럼 스케일이 다른 변수를 공평하게 비교하기 위함
samples_norm = (samples - LO) / (HI - LO)
dists_norm = pdist(samples_norm)
print(f"\n[정규화 공간 기준 — 스케일이 다른 변수를 공평하게 비교]")
print(f"최소 샘플 간 거리: {dists_norm.min():.4f}")
print(f"평균 샘플 간 거리: {dists_norm.mean():.4f}")

# 참고: 원래 값(mm/deg 혼재) 그대로 잰 거리도 같이 출력 — V1과 비교하고 싶을 때만 참고
dists_raw = pdist(samples)
print(f"\n[참고 — 원래 값 그대로, mm/deg 혼재라 각도 변수가 거리 지배]")
print(f"최소 샘플 간 거리: {dists_raw.min():.4f}")
print(f"평균 샘플 간 거리: {dists_raw.mean():.4f}")
