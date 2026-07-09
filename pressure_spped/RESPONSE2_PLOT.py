# RESPONSE2_PLOT.py
# 설계공간(X=각도, Y=두께) 상 예측결과(Z) 3D 표면 시각화
# 목적함수: 차압 + 핀뱅크 입구 속도CV (온도/온도편차는 기록용, 모델 학습에는 미사용)
# Jupyter에서 셀 단위로 실행

# %%
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa

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

mu_p = np.exp(gpr_dp.predict(gs)).reshape(A.shape)   # log → 원래 단위 (차압)
mu_c = gpr_cv.predict(gs).reshape(A.shape)

# %%
# 각 목적함수별 최소 지점을 따로 탐색 (차압-CV는 트레이드오프라 단일 최적점 아님, 참고용)
def _best_point(Z):
    i, j = np.unravel_index(np.argmin(Z), Z.shape)
    return A[i, j], T[i, j], Z[i, j]

best_p_a, best_p_t, best_p_v = _best_point(mu_p)
best_c_a, best_c_t, best_c_v = _best_point(mu_c)

print("=== 각 목적함수별 예측 최적점 (참고용 — 실제 선택은 파레토/무릎점 분석 참조) ===")
print(f"차압 최소:   각도={best_p_a:.0f}°, 두께={best_p_t:.0f}mm  → {best_p_v:.2f}Pa")
print(f"속도CV 최소: 각도={best_c_a:.0f}°, 두께={best_c_t:.0f}mm  → {best_c_v:.2f}%")

# %%
# 한 화면에 2개 3D 서브플롯으로 표시
fig = plt.figure(figsize=(14, 7))


def _surface(ax, Z, title, cmap, zlabel, best):
    surf = ax.plot_surface(A, T, Z, cmap=cmap, alpha=0.85, linewidth=0, antialiased=True)
    ax.scatter(df["angle"], df["thickness"],
               [Z[np.argmin(np.abs(a_cands-a)), np.argmin(np.abs(t_cands-t))]
                for a, t in zip(df["angle"], df["thickness"])],
               c="black", s=25, marker="x", depthshade=False, label="실험점")
    ba, bt, bv = best
    ax.scatter([ba], [bt], [bv],
               c="red", s=250, marker="*", depthshade=False, zorder=10, label="최적점")
    ax.set_xlabel("각도 (°)")
    ax.set_ylabel("유로두께 (mm)")
    ax.set_zlabel(zlabel)
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8)
    fig.colorbar(surf, ax=ax, shrink=0.5, pad=0.1)

ax1 = fig.add_subplot(121, projection="3d")
_surface(ax1, mu_p, "차압 (★=차압 최소점)", "Blues", "차압 (Pa)", (best_p_a, best_p_t, best_p_v))

ax2 = fig.add_subplot(122, projection="3d")
_surface(ax2, mu_c, "속도CV (★=CV 최소점)", "viridis", "속도CV (%)", (best_c_a, best_c_t, best_c_v))

plt.tight_layout()
PLOT_DIR = r"E:\Thermal_Anlaysis\260708\plot"
os.makedirs(PLOT_DIR, exist_ok=True)
save_path = os.path.join(PLOT_DIR, "response_surface_all_ps.png")
plt.savefig(save_path, dpi=150, bbox_inches="tight")
plt.show()
print(f"저장 완료: {save_path}")
