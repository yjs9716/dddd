"""
GPR의 예측 불확실도(σ)가 실제 예측오차와 얼마나 비례하는지 확인.

배경 — V4에서 미해결로 남은 문제
  적응샘플링(IMSE)은 "불확실도가 큰 곳을 찍으면 모델이 빨리 좋아진다"를 전제한다.
  그런데 V4 데이터(211점)로 검정해보니 레인 유량 일부는 σ와 실제오차의 상관이
  통계적으로 0이었고(lane2_01/lane2_04는 95% 부트스트랩 신뢰구간이 0을 좁게 감쌈),
  lane1_01은 오히려 유의한 음의 상관이었다. 반면 pressure_drop은 상관이 뚜렷했다.

  원인 후보를 세 가지 세워서 전부 실측으로 기각했다:
    · WhiteKernel noise_level 상한이 너무 헐거움 → 상한을 조여도 상관 개선 없음
    · Matern length_scale 상한(50)이 너무 헐거움 → 500으로 늘려도 변화 없음
    · 8차원에 200점은 너무 성김(차원의 저주) → 최근접거리 실측으로 반박됨
  근본 원인은 확정하지 못했다. V5에서 변수가 10개로 늘고 레인 정의도 바뀌었으니
  같은 현상이 재현되는지 다시 봐야 한다 — 그게 이 스크립트의 용도다.

읽는 법
  Spearman r > 0.3   : σ를 믿고 IMSE를 쓸 수 있음
  0.1 ~ 0.3          : 약함 — 적응샘플링 효율이 떨어질 수 있음
  < 0.1              : 거의 무관 — 그 지표에 대해서는 IMSE가 사실상 무작위 탐색

  σ가 안 믿긴다고 해서 결과가 틀리는 건 아니다(모델 정확도는 종료기준으로 따로 검증함).
  다만 "IMSE 기반으로 효율적으로 샘플링했다"는 주장은 그만큼 약해지므로,
  논문/보고서에 쓸 때는 이 결과를 숨기지 말고 있는 그대로 적을 것.

사용법
  260827\\Code 안에서: python check_calibration.py
  (results_v5.csv가 있는 폴더 기준. 최소 30점 이상 쌓였을 때 의미 있는 결과)
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from scipy.stats import spearmanr, pearsonr

from OLHD import PARAM_NAMES, normalize
from ML import _load_results, _fit_gpr, OBJECTIVES

N_REPS = 15
TRAIN_FRAC = 0.7


def main():
    df = _load_results()
    n = len(df)
    if n < 30:
        print(f"데이터가 {n}점뿐 — 최소 30점은 쌓인 뒤에 의미 있는 결과가 나옵니다.")
        return

    X = normalize(df[PARAM_NAMES].values)
    rng = np.random.default_rng(0)
    n_train = int(n * TRAIN_FRAC)

    print(f"현재 {n}점 데이터로 검증 "
          f"(매회 {n_train}점 학습 / 나머지 {n - n_train}점으로 테스트, {N_REPS}회 반복)\n")
    print(f"{'지표':>16s} {'Pearson r':>10s} {'Spearman r':>11s}   판정")

    for name, use_log in OBJECTIVES:
        yr = df[name].values.astype(float)
        y = np.log(yr) if use_log else yr
        sig_all, err_all = [], []
        for _ in range(N_REPS):
            idx = rng.permutation(n)
            tr, te = idx[:n_train], idx[n_train:]
            if len(te) < 5:
                continue
            gpr = _fit_gpr(X[tr], y[tr])
            p, s = gpr.predict(X[te], return_std=True)
            if use_log:
                p = np.exp(p)
                s = s * p   # log스케일 σ를 원단위로 근사 환산(델타법)
            sig_all.extend(s)
            err_all.extend(np.abs(p - yr[te]))

        r_p, _ = pearsonr(sig_all, err_all)
        r_s, _ = spearmanr(sig_all, err_all)
        verdict = "비례함" if r_s > 0.3 else ("약함" if r_s > 0.1 else "거의 무관")
        print(f"{name:>16s} {r_p:10.3f} {r_s:11.3f}   {verdict}")

    print("\n비교 기준 — V4(211점): pressure_drop 뚜렷 / 레인 일부는 상관 0 "
          "(lane1_01은 유의한 음의 상관)")
    print("V5에서 레인이 pressure_drop 수준으로 올라오면 V4의 문제가 "
          "레인 정의(압축·측정위치) 탓이었다는 뜻이고, 그대로면 다른 원인이 있다는 뜻입니다.")


if __name__ == "__main__":
    main()
