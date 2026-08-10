"""
V2 유로 7변수 Optimal Latin Hypercube Design

V1(2변수) 대비 변경점
  - d=2 → d=7
  - 변수 범위를 PARAM_SPEC 한 곳에서만 정의 (ML.py가 이걸 import해서 씀)
  - maxmin 후보 탐색 횟수 100 → 200 (차원이 늘어 한 번에 좋은 배치가 잘 안 나옴)
"""
import numpy as np
from scipy.stats import qmc

# ── 설계변수 정의 (이름, 하한, 상한) ─────────────────────────────
#    이름은 SolidWorks 글로벌 변수명과 반드시 일치해야 함
PARAM_SPEC = [
    ("input_thick",        15.0, 35.0),   # mm
    ("input_angle",        90.0, 150.0),  # deg
    ("power_input_thick",  10.0, 40.0),   # mm
    ("power_output_thick", 15.0, 40.0),   # mm
    ("mid_thick",          15.0, 35.0),   # mm
    ("mid_angle",          90.0, 140.0),  # deg
    ("output_thick",       15.0, 35.0),   # mm
]

PARAM_NAMES = [p[0] for p in PARAM_SPEC]
LO = np.array([p[1] for p in PARAM_SPEC], dtype=float)
HI = np.array([p[2] for p in PARAM_SPEC], dtype=float)
N_DIM = len(PARAM_SPEC)


def generate_olhd(n_samples=70, seed=42):
    """
    Optimal Latin Hypercube Design (7변수)
    반환: (n_samples, 7) numpy array — 실제 설계값, 소수점 첫째자리 반올림
    """
    sampler = qmc.LatinHypercube(d=N_DIM, seed=seed)
    best_sample  = sampler.random(n=n_samples)
    best_mindist = _min_dist(best_sample)

    # maxmin 최적화: 여러 seed 중 최소거리 최대인 배치 선택
    for s in range(200):
        candidate = qmc.LatinHypercube(d=N_DIM, seed=seed + s + 1).random(n=n_samples)
        md = _min_dist(candidate)
        if md > best_mindist:
            best_mindist = md
            best_sample  = candidate

    scaled = qmc.scale(best_sample, LO, HI)
    return np.round(scaled, 1)


def _min_dist(sample):
    """샘플 간 최소 유클리드 거리"""
    from scipy.spatial.distance import pdist
    return pdist(sample).min()


def to_dict(row):
    """(7,) 배열 → {변수명: 값} 딕셔너리"""
    return {name: float(v) for name, v in zip(PARAM_NAMES, row)}


if __name__ == "__main__":
    samples = generate_olhd(n_samples=70, seed=42)
    print(f"OLHD 샘플 {len(samples)}점 ({N_DIM}변수)")
    print("  " + "  ".join(f"{n:>18s}" for n in PARAM_NAMES))
    for i, row in enumerate(samples):
        print(f"{i+1:3d}: " + "  ".join(f"{v:18.1f}" for v in row))
