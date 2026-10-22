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
  · maxmin 최적화: V5는 무작위 LHS 여러 개 중 최선을 골랐다(시도를 늘려도 거의 안 좋아짐 —
    80점·8변수에서 100회 0.42 → 10만 회 0.45). V6는 그 최선을 출발점으로 열 내 교환 탐색을 한다:
    한 변수 열에서 두 점의 값을 맞바꿔 최소 거리가 줄지 않으면 채택(같은 열 안의 교환이라
    LHS 성질은 유지). 5만 회에 약 35초, 최소 거리 0.44 → 0.69.
  · 만든 실험점은 olhd_plan.csv 에 저장하고 이후엔 그대로 읽는다(get_olhd_plan) —
    main.py 를 껐다 켜도 점 목록이 바뀌지 않게 (DSD.get_plan 과 같은 방식).
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.spatial.distance import pdist

from params import CANDIDATES, Screening, STAGE2_FOLD, to_dict
from fins import BANKS, bank_gap, all_banks_feasible
from paths import SCREENING_PATH, OLHD_PLAN_PATH, OLHD_PLAN_META_PATH

N_START_TRIALS = 1000     # 출발점: 무작위 LHS 중 최소 거리 최대
N_SWAP_ITERS   = 50000    # 열 내 교환 탐색 반복 수


def default_n_doe(screening):
    return 10 * screening.n_dim


def _min_dist(screening, u):
    return pdist(screening.normalize_active(screening.decode_active(u))).min()


def generate_olhd(screening, n_samples=None, seed=42, n_start=N_START_TRIALS, n_swap=N_SWAP_ITERS):
    """반환: ((n_samples, 11) 실제 설계값, 최소 거리). 모든 행이 뱅크별 갭 제약을 만족한다."""
    n_samples = n_samples or default_n_doe(screening)
    d = screening.n_dim

    u, md = None, -np.inf
    for s in range(n_start):
        cand = qmc.LatinHypercube(d=d, seed=seed + s).random(n=n_samples)
        m = _min_dist(screening, cand)
        if m > md:
            u, md = cand, m

    rng = np.random.default_rng(seed)
    for _ in range(n_swap):
        j = rng.integers(d)
        a, b = rng.choice(n_samples, 2, replace=False)
        v = u.copy()
        v[[a, b], j] = v[[b, a], j]
        m = _min_dist(screening, v)
        if m >= md:        # 같으면 받아들여 평탄한 구간을 건너감
            u, md = v, m

    x = screening.decode_active(u)
    bad = [i for i, r in enumerate(x) if not all_banks_feasible(to_dict(r, False))]
    if bad:
        raise RuntimeError(f"갭 제약 위반 샘플이 생성됨(decode 버그): 행 {bad}")
    return x, float(md)


def _plan_key(screening):
    """실험점을 만든 조건 — 저장된 계획이 지금 선별 결과와 맞는지 비교용."""
    return {"active": list(screening.active),
            "fixed_u": {k: float(v) for k, v in screening.fixed_u.items()},
            "fold": STAGE2_FOLD,
            "n_samples": default_n_doe(screening)}


def get_olhd_plan(screening):
    """OLHD 실험점 (n, 11) 실제 설계값. olhd_plan.csv 가 있으면 그대로 읽고, 없으면 만들어 저장."""
    key = _plan_key(screening)
    if os.path.exists(OLHD_PLAN_PATH):
        if not os.path.exists(OLHD_PLAN_META_PATH):
            raise RuntimeError(f"{OLHD_PLAN_META_PATH} 가 없음 — olhd_plan.csv 를 만든 조건을 확인할 수 없다")
        with open(OLHD_PLAN_META_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        if saved["key"] != key:
            raise RuntimeError(
                "저장된 OLHD 실험점이 지금 선별 결과와 다름\n"
                f"  저장: {saved['key']}\n  현재: {key}\n"
                "  → OLHD 해석을 아직 시작 전이라면 olhd_plan.csv / olhd_plan_meta.json 을 지우고 다시 실행")
        return pd.read_csv(OLHD_PLAN_PATH)[CANDIDATES].values.astype(float)

    print(f"OLHD 실험점 생성 중 (활성 {screening.n_dim}변수, {key['n_samples']}점, 약 40초)...")
    x, md = generate_olhd(screening)
    rows = []
    for i, r in enumerate(x):
        p = to_dict(r, include_fixed_geometry=False)
        row = {"idx": i}
        row.update(p)
        row.update({f"fin_gap_{b}": bank_gap(p, b) for b in BANKS})
        rows.append(row)
    os.makedirs(os.path.dirname(OLHD_PLAN_PATH), exist_ok=True)
    pd.DataFrame(rows).to_csv(OLHD_PLAN_PATH, index=False)
    with open(OLHD_PLAN_META_PATH, "w", encoding="utf-8") as f:
        json.dump({"key": key, "min_dist": md, "n_start": N_START_TRIALS, "n_swap": N_SWAP_ITERS},
                  f, ensure_ascii=False, indent=2)
    print(f"  저장: {OLHD_PLAN_PATH} (최소 거리 {md:.4f})")
    return x


if __name__ == "__main__":
    sc = Screening(SCREENING_PATH)
    X = get_olhd_plan(sc)
    print(f"OLHD {len(X)}점 (활성 {sc.n_dim}변수: {sc.active})")
    print(f"고정 변수(대표값): {sc.fixed_values()}")
    print(f"최소 샘플 간 거리(정규화): {pdist(sc.normalize_active(X)).min():.4f}")
