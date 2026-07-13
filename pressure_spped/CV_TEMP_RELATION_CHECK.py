# CV_TEMP_RELATION_CHECK.py
# 속도CV(vel_cv)는 실제 관심사(온도 균일도)의 대리지표(proxy)로 목적함수에 쓰였을 뿐,
# 진짜 판단 기준은 온도(max_temp)/온도편차(temp_std)다.
# 185개 실측 데이터로 "CV 10%/20%/... 일 때 실제 온도편차/최고온도가 얼마나 다른지"를
# 이 시스템 고유의 경험적 관계로 직접 확인한다.
# Jupyter에서 셀 단위로 실행 (results_ps.csv 있는 환경에서)

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ML import RESULTS_PATH

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_csv(RESULTS_PATH)
df = df.dropna(subset=["vel_cv", "temp_std", "max_temp"])
print(f"온도 데이터 있는 실측점: {len(df)}개")

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

def scatter_with_fit(ax, x, y, ylabel):
    ax.scatter(x, y, c="tab:blue", s=25, alpha=0.6, label="실측점")
    coef = np.polyfit(x, y, deg=1)
    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = np.polyval(coef, x_line)
    ax.plot(x_line, y_line, "r-", linewidth=2,
            label=f"선형추세: y={coef[0]:.4f}x+{coef[1]:.3f}")
    r = np.corrcoef(x, y)[0, 1]
    ax.set_xlabel("속도 CV (%)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} vs 속도CV  (상관계수 r={r:.3f})")
    ax.legend(fontsize=8)
    return coef

coef_std  = scatter_with_fit(axes[0], df["vel_cv"].values, df["temp_std"].values, "온도편차 temp_std (°C)")
coef_maxt = scatter_with_fit(axes[1], df["vel_cv"].values, df["max_temp"].values, "최고온도 max_temp (°C)")

plt.tight_layout()
plt.show()

# %%
print("\n=== 선형추세 기준, CV별 예상 온도편차/최고온도 (참고용 외삽 포함) ===")
print(" CV(%) | 예상 temp_std(°C) | 예상 max_temp(°C)")
for cv in [10, 12, 14, 16, 18, 20, 22, 24, 26]:
    est_std  = np.polyval(coef_std, cv)
    est_maxt = np.polyval(coef_maxt, cv)
    in_range = "" if df["vel_cv"].min() <= cv <= df["vel_cv"].max() else "  (범위 밖 외삽 주의)"
    print(f"  {cv:4d}  |      {est_std:6.3f}       |      {est_maxt:7.3f}{in_range}")

print(f"\n실측 vel_cv 범위: {df['vel_cv'].min():.1f}% ~ {df['vel_cv'].max():.1f}%")

# %%
# 두 무릎점 후보 근방 실측점 비교 (MRS기준 dp≈1450 vs 가중치기준 dp≈1730)
for label, dp_target in [("한계대체율 무릎(dp≈1450)", 1450), ("가중치 무릎(dp≈1730)", 1730)]:
    near = df.iloc[(df["pressure_drop"] - dp_target).abs().argsort()[:3]]
    print(f"\n[{label}] 근접 실측점 3개:")
    print(near[["idx", "angle", "thickness", "pressure_drop", "vel_cv", "max_temp", "temp_std"]]
          .to_string(index=False))
