"""
GPR의 예측 불확실도(σ)가 실제 예측오차와 얼마나 비례하는지 확인.

배경
  V3 데이터로 CV(vel_cv_pass1/2)와 temp_std(둘 다 여러 값을 하나로 압축한 지표)를
  검사했더니 σ와 실제오차의 상관이 거의 없었음(Spearman 0.03~0.09). 반면 압축이
  없는 pressure_drop은 상관이 뚜렷했음(0.42). "압축된 지표일수록 σ를 못 믿는다"는
  가설이 맞다면, V4에서 압축 없이 직접 학습하는 레인 개별 유량(lane1_XX/lane2_XX)은
  pressure_drop처럼 상관이 좋아야 한다 — 이걸 실측으로 확인하는 스크립트.

사용법
  260821\\Code 안에서: python check_calibration.py
  (results_v4.csv가 있는 폴더에서 실행. 최소 30점 이상 쌓였을 때 의미 있는 결과)
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from scipy.stats import spearmanr, pearsonr

from OLHD import PARAM_NAMES, LO, HI
from ML import _load_results, _fit_gpr, OBJECTIVES, N_DOE


def main():
    df = _load_results()
    n = len(df)
    if n < 30:
        print(f"데이터가 {n}점뿐 — 최소 30점은 쌓인 뒤에 의미 있는 결과가 나옵니다.")
        return

    X = (df[PARAM_NAMES].values - LO) / (HI - LO)
    rng = np.random.default_rng(0)
    n_train = int(n * 0.7)   # 나머지 30%(최소 9점 이상 보장되도록 위에서 n>=30 체크)
    n_reps = 15

    print(f"현재 {n}점 데이터로 검증 (매회 {n_train}점 학습 / 나머지로 테스트, {n_reps}회 반복)\n")
    print(f"{'지표':>16s} {'Pearson r':>10s} {'Spearman r':>11s}   판정")

    for name, use_log in OBJECTIVES:
        yr = df[name].values.astype(float)
        y = np.log(yr) if use_log else yr
        sig_all, err_all = [], []
        for _ in range(n_reps):
            idx = rng.permutation(n)
            tr, te = idx[:n_train], idx[n_train:]
            if len(te) < 5:
                continue
            gpr = _fit_gpr(X[tr], y[tr])
            p, s = gpr.predict(X[te], return_std=True)
            if use_log:
                p = np.exp(p)
                s = s * p  # log스케일 σ를 원단위로 근사 환산(델타법)
            sig_all.extend(s)
            err_all.extend(np.abs(p - yr[te]))

        r_p, _ = pearsonr(sig_all, err_all)
        r_s, _ = spearmanr(sig_all, err_all)
        verdict = "비례함" if r_s > 0.3 else ("약함" if r_s > 0.1 else "거의 무관")
        print(f"{name:>16s} {r_p:10.3f} {r_s:11.3f}   {verdict}")

    print("\n비교 기준(V3 데이터, 139점): pressure_drop 0.419(비례함) / "
          "temp_std 0.090(무관) / vel_cv_pass2 0.029(무관)")
    print("레인 유량(lane1_XX/lane2_XX)들이 pressure_drop 수준으로 나오면 "
          "'압축 없는 지표는 σ를 믿을 수 있다'는 가설이 확인되는 것입니다.")


if __name__ == "__main__":
    main()
