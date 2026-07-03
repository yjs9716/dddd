import numpy as np
from scipy.stats import qmc
from scipy.spatial.distance import pdist

# 설계공간 (ML_final.py에서도 이 값을 import해서 사용)
ANGLE_MIN, ANGLE_MAX = 0, 30    # 각도 [deg]
THICK_MIN, THICK_MAX = 15, 40   # 유로두께 [mm]

N_SEED_SEARCH = 100000  # maxmin 최적화 시드 탐색 횟수 (실험 시작 후 절대 변경 금지!)


def generate_olhd(n_samples=20, seed=42):
    """
    Optimal Latin Hypercube Design (LHS + maxmin)
    변수: [각도, 유로두께]
    반환: (n_samples, 2) numpy array - 정수 반올림된 실제 설계값

    주의: 이 함수의 결과는 실험 진행상태(results.csv)의 idx와 1:1 대응됨.
          실험 시작 후 seed, n_samples, N_SEED_SEARCH를 바꾸면
          이미 완료된 실험과 어긋나므로 절대 변경하지 말 것.
    """
    best_sample  = qmc.LatinHypercube(d=2, seed=seed).random(n=n_samples)
    best_mindist = _min_dist(best_sample)

    for s in range(N_SEED_SEARCH):
        candidate = qmc.LatinHypercube(d=2, seed=seed + s + 1).random(n=n_samples)
        md = _min_dist(candidate)
        if md > best_mindist:
            best_mindist = md
            best_sample  = candidate

    # [0,1] → 실제 설계값으로 스케일
    scaled = qmc.scale(best_sample, [ANGLE_MIN, THICK_MIN], [ANGLE_MAX, THICK_MAX])

    # 각도/두께 모두 정수 반올림 (STEP 파일명 및 격자 탐색과 일관성 유지)
    scaled = np.round(scaled)

    return scaled


def _min_dist(sample):
    """샘플 간 최소 유클리드 거리"""
    return pdist(sample).min()


if __name__ == "__main__":
    samples = generate_olhd(n_samples=20, seed=42)
    print("OLHD 샘플 (각도, 유로두께):")
    for i, (a, t) in enumerate(samples):
        print(f"  {i+1:2d}: 각도={a:5.1f}°  유로두께={t:5.1f}mm")
    print(f"\n최소 샘플 간 거리: {pdist(samples).min():.3f}")
    print(f"평균 샘플 간 거리: {pdist(samples).mean():.3f}")
