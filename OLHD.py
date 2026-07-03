import numpy as np
from scipy.stats import qmc

def generate_olhd(n_samples=20, seed=42):
    """
    Optimal Latin Hypercube Design
    변수: [각도(0~30), 유로두께(15~40)]
    반환: (n_samples, 2) numpy array - 실제 설계값
    """
    sampler = qmc.LatinHypercube(d=2, seed=seed)
    sample  = sampler.random(n=n_samples)

    # maxmin 최적화: 여러 seed 중 최소 거리 최대인 것 선택
    best_sample  = sample
    best_mindist = _min_dist(sample)

    for s in range(100):
        candidate = qmc.LatinHypercube(d=2, seed=seed + s + 1).random(n=n_samples)
        md = _min_dist(candidate)
        if md > best_mindist:
            best_mindist = md
            best_sample  = candidate

    # [0,1] → 실제 설계값으로 스케일
    l_bounds = [0,  15]   # 각도 최소, 유로두께 최소
    u_bounds = [30, 40]   # 각도 최대, 유로두께 최대
    scaled = qmc.scale(best_sample, l_bounds, u_bounds)

    # 각도는 정수로 반올림
    scaled[:, 0] = np.round(scaled[:, 0]).astype(int)

    return scaled

def _min_dist(sample):
    """샘플 간 최소 유클리드 거리"""
    from scipy.spatial.distance import pdist
    return pdist(sample).min()


if __name__ == "__main__":
    samples = generate_olhd(n_samples=20, seed=42)
    print("OLHD 샘플 (각도, 유로두께):")
    for i, (a, t) in enumerate(samples):
        print(f"  {i+1:2d}: 각도={a:5.1f}°  유로두께={t:5.1f}mm")
