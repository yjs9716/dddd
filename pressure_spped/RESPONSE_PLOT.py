# RESPONSE_PLOT.py
# 최종 결과에 대한 설계공간 내 예측분포(결과 장) 시각화
# 목적함수: 차압 + 핀뱅크 입구 속도CV (온도/온도편차는 기록용, 모델 학습에는 미사용)
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
print(df[["idx", "angle", "thickness", "pressure_drop", "vel_cv", "max_temp", "temp_std"]])

# %%
# 전체 데이터로 모델 2개(차압, 속도CV) 재학습
gpr_dp, gpr_cv = _fit_models(df)

# 설계공간 격자 (1도/1mm 간격)
a_cands = np.arange(_LO[0], _HI[0] + 1, 1)
t_cands = np.arange(_LO[1], _HI[1] + 1, 1)
A, T = np.meshgrid(a_cands, t_cands, indexing="ij")
grid = np.column_stack([A.ravel(), T.ravel()])
gs   = (grid - _LO) / (_HI - _LO)

mu_p, sig_p = gpr_dp.predict(gs, return_std=True)
mu_c, sig_c = gpr_cv.predict(gs, return_std=True)
mu_p = np.exp(mu_p)   # log → 원래 단위 (차압)

shape = A.shape
Z_dp, Z_cv = mu_p.reshape(shape), mu_c.reshape(shape)
Zsig_dp, Zsig_cv = sig_p.reshape(shape), sig_c.reshape(shape)

# %%
fig, axes = plt.subplots(2, 2, figsize=(13, 11))
fig.suptitle(f"설계공간 예측분포 (실험 {len(df)}회 기준)", fontsize=14, fontweight="bold")

def _draw(ax, Z, title, cmap):
    cf = ax.contourf(A, T, Z, levels=20, cmap=cmap)
    plt.colorbar(cf, ax=ax)
    ax.scatter(df["angle"], df["thickness"], c="black", s=20, marker="x", label="실험점")
    ax.set_xlabel("각도 (°)")
    ax.set_ylabel("유로두께 (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)

_draw(axes[0, 0], Z_dp,   "차압 예측 [Pa]", "Blues")
_draw(axes[0, 1], Z_cv,   "속도CV 예측 [%]", "viridis")

_draw(axes[1, 0], Zsig_dp, "log차압 예측 불확실성 (σ)", "Greys")
_draw(axes[1, 1], Zsig_cv, "속도CV 예측 불확실성 (σ)", "Greys")

plt.tight_layout()
PLOT_DIR = r"E:\Thermal_Anlaysis\260708\plot"
os.makedirs(PLOT_DIR, exist_ok=True)
save_path = os.path.join(PLOT_DIR, "response_surface_ps.png")
plt.savefig(save_path, dpi=150, bbox_inches="tight")
plt.show()
print(f"저장 완료: {save_path}")

# %%
# 차압-속도CV는 트레이드오프 관계라 단일 "최적점"이 없음 (파레토 문제)
# 참고용으로 각 목적함수 단독 최소점과, 격자 위에서 재계산한 파레토 프론트를 같이 출력
best_dp_i = np.argmin(Z_dp)
best_cv_i = np.argmin(Z_cv)
print(f"\n[참고] 예측 차압 최소 지점  : 각도={grid[best_dp_i,0]:.0f}°, 두께={grid[best_dp_i,1]:.0f}mm"
      f"  (예측차압={Z_dp.ravel()[best_dp_i]:.1f}Pa, 예측CV={Z_cv.ravel()[best_dp_i]:.2f}%)")
print(f"[참고] 예측 속도CV 최소 지점: 각도={grid[best_cv_i,0]:.0f}°, 두께={grid[best_cv_i,1]:.0f}mm"
      f"  (예측차압={Z_dp.ravel()[best_cv_i]:.1f}Pa, 예측CV={Z_cv.ravel()[best_cv_i]:.2f}%)")

# 격자 예측값 기준 파레토 프론트 (둘 다 최소화)
dp_flat, cv_flat = Z_dp.ravel(), Z_cv.ravel()
order = np.argsort(dp_flat)
pareto_mask = np.zeros(len(dp_flat), dtype=bool)
min_cv_so_far = np.inf
for i in order:  # 차압 오름차순으로 훑으며 CV 최솟값 갱신 기록 = 파레토 프론트
    if cv_flat[i] < min_cv_so_far:
        pareto_mask[i] = True
        min_cv_so_far = cv_flat[i]
print(f"\n[참고] 격자 기준 파레토 프론트 포인트 수: {pareto_mask.sum()}")
print("       (차압을 최소~최대로 정렬했을 때 CV가 갱신 최소를 찍는 지점들 — "
      "실제 설계값 선택은 무릎점/가중치 분석으로 별도 진행)")
