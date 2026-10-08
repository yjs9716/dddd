# %%
"""
V6 OLHD 샘플 분포 시각화 — 활성 변수 개수와 무관하게 동작

V5(Code/OLHD_PLOT.py) 대비 변경점
  · 변수 목록이 screening_decision.json(1단계 DSD 선별 결과)에서 정해진다.
    활성 변수만 그리고, 고정 변수와 그 값은 제목에 적는다.
  · main.py(ML.py)와 같은 generate_olhd(screening, seed=42)를 써서 실제로 돌릴 점과 똑같은 점을 그린다.
  · 거리는 OLHD 생성 때와 같은 "활성 변수 박스 정규화 공간"에서 잰다.
  · 2단계는 핀 두께를 개수에 따라 접으므로(params.STAGE2_FOLD) 핀 두께 히스토그램은 얇은 쪽으로
    치우친다 — 정상이다(많은 개수는 얇은 핀으로만 가능). 핀 개수는 10~24에 고르게 퍼진다.
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist

from OLHD import generate_olhd
from params import Screening
from paths import SCREENING_PATH

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

POINT = "#2a78d6"     # 점·막대 색 (한 계열)
INK = "#52514e"       # 축·눈금 글자
GRID = "#e4e3df"      # 격자선

# %%
sc = Screening(SCREENING_PATH)
names = sc.active
n_dim = sc.n_dim
lo, hi = sc.lo, sc.hi

X_full = generate_olhd(sc, seed=42)        # (n, 11) 실제 설계값 — main.py가 돌릴 점과 동일
samples = X_full[:, sc.idx_active]          # 활성 변수만
n = len(samples)
fixed = sc.fixed_values()
fixed_txt = ", ".join(f"{k}={float(v):g}" for k, v in fixed.items())

print(f"OLHD 샘플 {n}개 (활성 {n_dim}변수)")
print(f"고정 변수: {fixed_txt}")
print("     " + "  ".join(f"{name:>17s}" for name in names))
for i, row in enumerate(samples):
    print(f"{i+1:3d}: " + "  ".join(f"{v:17.1f}" for v in row))


def _bins(i):
    """히스토그램 구간. 핀 두께(0.1mm 반올림)·개수(정수)처럼 수준이 적은 변수는 수준마다 한 칸 —
    10칸으로 나누면 수준이 칸에 고르게 안 들어가 들쭉날쭉해 보인다."""
    levels = np.unique(samples[:, i])
    step = np.min(np.diff(levels)) if len(levels) > 1 else 1.0
    n_levels = int(round((hi[i] - lo[i]) / step)) + 1
    if n_levels <= 30:
        return lo[i] - step / 2 + step * np.arange(n_levels + 1)
    return np.linspace(lo[i], hi[i], 11)


def _title(name):
    return f"{name} (개수에 따라 상한 접힘)" if name.startswith("fin_thick") else name


def _style(ax):
    ax.tick_params(colors=INK, labelsize=6)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.grid(color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)


# %%
# --- 변수별 분포 균일성 (marginal histogram) ---
n_cols = 4
n_rows = int(np.ceil(n_dim / n_cols))
fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3.2 * n_rows))
fig.suptitle(f"변수별 분포 균일성 (OLHD {n}점, 활성 {n_dim}변수)\n고정: {fixed_txt}",
             fontsize=13, fontweight="bold")
axes = np.array(axes).reshape(-1)

for i, name in enumerate(names):
    ax = axes[i]
    edges = _bins(i)
    ax.hist(samples[:, i], bins=edges, color=POINT, edgecolor="white", linewidth=2)
    ax.set_title(_title(name), fontsize=10)
    ax.set_xlabel("값", fontsize=9, color=INK)
    ax.set_ylabel("빈도", fontsize=9, color=INK)
    ax.set_xlim(edges[0], edges[-1])
    _style(ax)
    ax.tick_params(labelsize=8)

for j in range(n_dim, len(axes)):
    axes[j].axis("off")

plt.tight_layout()
plt.savefig("OLHD_marginal.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: OLHD_marginal.png")

# %%
# --- 변수쌍 산점도 (하삼각) — 설계공간 커버리지 확인용 ---
#   대각선: 각 변수의 분포(위 히스토그램과 같은 정보)
#   하삼각: 두 변수 조합에서 점이 고르게 퍼져 있는지 (특정 구석에 몰려있으면 안 됨)
fig2, axes2 = plt.subplots(n_dim, n_dim, figsize=(2.2 * n_dim, 2.2 * n_dim))
fig2.suptitle(f"변수쌍 산점도 (설계공간 커버리지, {n}점)\n고정: {fixed_txt}",
              fontsize=13, fontweight="bold")

for i in range(n_dim):
    for j in range(n_dim):
        ax = axes2[i, j]
        if i == j:
            edges = _bins(i)
            ax.hist(samples[:, i], bins=edges, color=POINT, edgecolor="white", linewidth=1)
            ax.set_xlim(edges[0], edges[-1])
        elif i > j:
            ax.scatter(samples[:, j], samples[:, i], s=10, color=POINT, alpha=0.8, linewidths=0)
            pad_x, pad_y = 0.03 * (hi[j] - lo[j]), 0.03 * (hi[i] - lo[i])   # 경계값 점이 잘리지 않게
            ax.set_xlim(lo[j] - pad_x, hi[j] + pad_x)
            ax.set_ylim(lo[i] - pad_y, hi[i] + pad_y)
        else:
            ax.axis("off")
            continue
        _style(ax)

        if i == n_dim - 1:
            ax.set_xlabel(names[j], fontsize=7, color=INK)
        else:
            ax.set_xticklabels([])
        if j == 0 and i != 0:
            ax.set_ylabel(names[i], fontsize=7, color=INK)
        elif j != 0 or i == 0:
            ax.set_yticklabels([])

plt.tight_layout()
plt.savefig("OLHD_pairwise.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: OLHD_pairwise.png")

# %%
# --- 최소/평균 거리, 상관 (공간 균일성 지표) ---
#   정규화 공간: OLHD 생성(maxmin) 때와 같은 활성 변수 박스 정규화
samples_norm = sc.normalize_active(X_full)
dists_norm = pdist(samples_norm)
print(f"\n[정규화 공간 기준 — 스케일이 다른 변수를 공평하게 비교]")
print(f"최소 샘플 간 거리: {dists_norm.min():.4f}")
print(f"평균 샘플 간 거리: {dists_norm.mean():.4f}")

# 변수쌍 상관계수 — 0에 가까울수록 변수끼리 독립적으로 퍼져 있음
#   같은 뱅크의 핀 두께-개수는 두께 상한이 개수에 따라 접혀서(많으면 얇아야 함) 음의 상관이
#   생긴다 — 설계 제약 때문이라 정상. 그 쌍을 뺀 값을 같이 출력한다.
r = np.corrcoef(samples_norm, rowvar=False)
pairs = [(a, b) for a in range(n_dim) for b in range(a + 1, n_dim)]
fold = {(f"fin_thick_{k}", f"fin_count_{k}") for k in (1, 2)}
for label, sel in (("전체", pairs),
                   ("핀 두께-개수 쌍 제외", [(a, b) for a, b in pairs
                                         if (names[a], names[b]) not in fold])):
    vals = np.array([abs(r[a, b]) for a, b in sel])
    a, b = sel[int(np.argmax(vals))]
    print(f"변수쌍 상관계수 [{label}] 최대 |r|: {vals.max():.3f} ({names[a]} - {names[b]}),"
          f"  평균 |r|: {vals.mean():.3f}")
