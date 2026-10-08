"""
V6 2단계 — 선별 후 활성 변수만으로 Optimal Latin Hypercube Design

V5(Code/OLHD.py) 대비 변경점
  · 변수 목록이 고정이 아니라 screening_decision.json(1단계 DSD 결과)에서 정해진다.
    LHS는 활성 변수 d_a 차원에서만 뽑고, 고정 변수는 선별 단계에서 정한 단위 좌표를
    끼워 넣은 뒤 params.decode()로 실제값을 만든다.
  · 핀 두께·개수 접어 넣기(갭 제약 보장)는 뱅크별로 적용된다(params.decode).
    2단계는 두께를 개수에 맞춰 접는다(params.STAGE2_FOLD = count_first) — 영향이 가장 큰
    핀 개수를 10~24 전 범위에 고르게 두기 위해서. 1단계 DSD는 V5와 같이 개수를 두께에 맞춰 접었다.
  · 점 수 = 10 × 활성 변수 수 (V5와 같은 경험칙).
  · maxmin 거리는 V5와 같이 "decode 후 활성 변수 박스 정규화 공간"에서 잰다.
"""
import numpy as np
from scipy.stats import qmc
from scipy.spatial.distance import pdist

from params import Screening
from fins import all_banks_feasible
from params import to_dict
from paths import SCREENING_PATH

N_MAXMIN_TRIALS = 20000


def default_n_doe(screening):
    return 10 * screening.n_dim


def generate_olhd(screening, n_samples=None, seed=42, n_trials=N_MAXMIN_TRIALS):
    """반환: (n_samples, 11) 실제 설계값. 모든 행이 뱅크별 갭 제약을 만족한다."""
    n_samples = n_samples or default_n_doe(screening)
    best_x, best_md = None, -np.inf
    for s in range(n_trials):
        u = qmc.LatinHypercube(d=screening.n_dim, seed=seed + s).random(n=n_samples)
        x = screening.decode_active(u)
        md = pdist(screening.normalize_active(x)).min()
        if md > best_md:
            best_md, best_x = md, x
    bad = [i for i, r in enumerate(best_x) if not all_banks_feasible(to_dict(r, False))]
    if bad:
        raise RuntimeError(f"갭 제약 위반 샘플이 생성됨(decode 버그): 행 {bad}")
    return best_x


if __name__ == "__main__":
    import time
    sc = Screening(SCREENING_PATH)
    t0 = time.time()
    X = generate_olhd(sc)
    print(f"OLHD {len(X)}점 (활성 {sc.n_dim}변수: {sc.active}), 생성 {time.time()-t0:.1f}초")
    print(f"고정 변수(대표값): {sc.fixed_values()}")
