# %%
# 결과 장(Response Surface) 시각화
# 실험이 어느 정도 쌓인 후(results.csv) Jupyter에서 셀 단위로 실행
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ML_final import (
    predict_grid, RESULTS_PATH,
    T_MAX_LIMIT, T_STD_LIMIT,
)

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# %%
df = pd.read_csv(RESULTS_PATH)
print(f"완료된 실험 수: {len(df)}")
print(df)

# %%
# GPR fitting 후 전체 설계공간 예측
grid, A, T, (mu_t, sig_t), (mu_s, sig_s), (mu_l, sig_l) = predict_grid(df)

shape  = A.shape
Z_temp = mu_t.reshape(shape)
Z_std  = mu_s.reshape(shape)
Z_dp   = np.exp(mu_l).reshape(shape)   # log 예측 → 원래 단위로
Z_sig  = sig_l.reshape(shape)

# 제약 만족 영역 + 추천점 (제약 만족 중 차압 최소)
feasible = (Z_temp <= T_MAX_LIMIT) & (Z_std <= T_STD_LIMIT)
Z_dp_feas = np.where(feasible, Z_dp, np.nan)
if feasible.any():
    bi, bj = np.unravel_index(np.nanargmin(Z_dp_feas), shape)
    best_a, best_t = A[bi, bj], T[bi, bj]
    print(f"추천 설계점: 각도={best_a}°, 유로두께={best_t}mm (예측 차압={Z_dp[bi, bj]:.1f})")
else:
    best_a = best_t = None
    print("제약을 만족하는 예측 영역이 없음 → 제약 상한 확인 필요")

# %%
fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.suptitle(f"결과 장 (실험 {len(df)}회 기준)", fontsize=14, fontweight="bold")

def _draw(ax, Z, title, cmap):
    cf = ax.contourf(A, T, Z, levels=20, cmap=cmap)
    plt.colorbar(cf, ax=ax)
    ax.scatter(df["angle"], df["thickness"], c="black", s=25, marker="x", label="실험점")
    if best_a is not None:
        ax.scatter([best_a], [best_t], c="red", s=200, marker="*", zorder=5, label="추천점")
    ax.set_xlabel("각도 (°)")
    ax.set_ylabel("유로두께 (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)

_draw(axes[0, 0], Z_temp, f"최대온도 예측 [°C] (제약 ≤ {T_MAX_LIMIT})", "hot_r")
_draw(axes[0, 1], Z_std,  f"온도 표준편차 예측 [°C] (제약 ≤ {T_STD_LIMIT})", "viridis")
_draw(axes[1, 0], Z_dp,   "차압 예측 [Pa] (목적함수: 최소화)", "Blues")
_draw(axes[1, 1], Z_sig,  "예측 불확실성 (log차압 std)", "Purples")

# 제약 만족 영역 외곽선 표시
axes[1, 0].contour(A, T, feasible.astype(int), levels=[0.5], colors="red", linewidths=2)

plt.tight_layout()
plt.savefig("response_surface.png", dpi=150, bbox_inches="tight")
plt.show()
print("저장 완료: response_surface.png")
