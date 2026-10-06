"""
V6 1단계 — 결정적 선별 설계(Definitive Screening Design, DSD) 실험표 생성

왜 DSD인가 (Plackett–Burman 대신)
  · 3수준(낮음/중간/높음)이라 변수별 곡률(중간값 최적 여부)까지 볼 수 있다 — PB는 2수준이라 못 봄.
  · 주효과가 2변수 상호작용과 섞이지 않는다(접는 구조 덕분).
  · 11변수 기준 29회로 PB+접는설계(24회)와 비슷한 비용.
  참고: Jones & Nachtsheim (2011) J. Quality Technology 43(1); (2017) Technometrics 59(3).

구성 (컨퍼런스 행렬 C, 크기 m)
  실험표 = [ C ; −C ; 0 ]  →  2m+1 회
    · 1~m 번   : C 의 각 행. 행마다 변수 하나만 0(중간), 나머지는 ±1(하한/상한)
    · m+1~2m 번: 1~m 번의 거울상(부호 전부 반전) — 주효과를 상호작용과 분리
    · 마지막   : 전부 0(범위 중앙) — 곡률 판단의 기준점
  C 는 Paley 구성법으로 만든다(q = m−1 이 소수일 때). C·Cᵀ = (m−1)·I 를 반드시 검증한다.

열 배정 (이 캠페인)
  변수 11개 + 가짜 인자(빈 열) 3개 = 14열 → m = 14, q = 13 → 29회.
  가짜 인자는 어떤 형상 치수와도 연결하지 않는 열이다. 실제로는 효과가 0이어야 하므로,
  분석 단계에서 이 열들의 추정치가 "효과 없음 기준선(잡음·별칭 바닥)"이 된다.
  열 배정은 아래 COLUMN_ORDER 로 고정한다(실험 전에 확정 — 결과를 보고 바꾸지 말 것).

수준 → 실제값
  수준 −1/0/+1 → 단위 좌표 u = 0/0.5/1 → params.decode()
  핀 개수는 "그 두께에서 허용되는 범위" 안의 비율로 해석되므로 −1 = 10개, +1 = 그 두께의 최대 개수.
  어떤 조합이든 갭 제약(≥ fins.MIN_GAP_MM = 2.0mm)을 만족하는 형상만 나온다.
"""
import os

import numpy as np
import pandas as pd

from params import CANDIDATES, N_CAND_DIM, decode, to_dict
from fins import BANKS, bank_gap, all_banks_feasible

N_FAKE = 3                       # 가짜 인자 수 (빈 열)
M = N_CAND_DIM + N_FAKE          # 컨퍼런스 행렬 크기 = 14
N_RUNS = 2 * M + 1               # 29
FAKE_NAMES = [f"fake_{i+1}" for i in range(N_FAKE)]
# 열 순서: 실제 변수 11개 → 가짜 인자 3개 (실험 전에 고정)
COLUMN_ORDER = list(CANDIDATES) + FAKE_NAMES


def _is_prime(q):
    return q > 1 and all(q % d for d in range(2, int(q ** 0.5) + 1))


def conference_matrix(m):
    """Paley 구성 컨퍼런스 행렬 (m×m), q = m−1 이 소수일 때.

    q ≡ 1 (mod 4) → 대칭형,  q ≡ 3 (mod 4) → 반대칭형.
    대각은 0, 나머지는 ±1, C·Cᵀ = (m−1)·I.
    """
    q = m - 1
    if not _is_prime(q):
        raise ValueError(f"m={m}: q=m−1={q} 이 소수가 아님 — 다른 크기를 쓰거나 가짜 인자 수를 조정할 것")
    residues = {(i * i) % q for i in range(1, q)}
    chi = lambda a: 0 if a % q == 0 else (1 if a % q in residues else -1)
    C = np.zeros((m, m), dtype=int)
    C[0, 1:] = 1
    C[1:, 0] = 1 if q % 4 == 1 else -1
    for i in range(q):
        for j in range(q):
            C[i + 1, j + 1] = chi(i - j)
    if not np.array_equal(C @ C.T, q * np.eye(m, dtype=int)):
        raise RuntimeError("컨퍼런스 행렬 검증 실패 (C·Cᵀ ≠ (m−1)·I)")
    return C


def coded_design():
    """(N_RUNS, M) 수준표 (−1/0/+1). 열 순서는 COLUMN_ORDER."""
    C = conference_matrix(M)
    return np.vstack([C, -C, np.zeros((1, M), dtype=int)])


def make_plan():
    """실험표 DataFrame: run, 수준(c_*), 실제 설계값, 뱅크별 갭."""
    L = coded_design()
    L_real = L[:, :N_CAND_DIM]
    X = decode((L_real + 1) / 2.0)

    rows = []
    for r in range(N_RUNS):
        p = to_dict(X[r], include_fixed_geometry=False)
        if not all_banks_feasible(p):
            raise RuntimeError(f"run {r}: 갭 제약 위반 — decode 버그")
        row = {"run": r}
        row.update({f"c_{n}": int(L[r, j]) for j, n in enumerate(COLUMN_ORDER)})
        row.update(p)
        row.update({f"fin_gap_{b}": bank_gap(p, b) for b in BANKS})
        rows.append(row)
    return pd.DataFrame(rows)


def design_checks(L):
    """수준표 성질 확인 — 주효과 열끼리 직교, 열마다 −1/0/+1 개수."""
    corr = np.corrcoef(L.T.astype(float))
    off = np.abs(corr - np.eye(L.shape[1])).max()
    counts = [(int((L[:, j] == -1).sum()), int((L[:, j] == 0).sum()), int((L[:, j] == 1).sum()))
              for j in range(L.shape[1])]
    return off, counts


def get_plan():
    """dsd_plan.csv 가 있으면 그대로 읽고(실행 중 실험표가 바뀌지 않게), 없으면 만들어 저장."""
    from paths import DSD_PLAN_PATH
    if os.path.exists(DSD_PLAN_PATH):
        return pd.read_csv(DSD_PLAN_PATH)
    plan = make_plan()
    os.makedirs(os.path.dirname(DSD_PLAN_PATH), exist_ok=True)
    plan.to_csv(DSD_PLAN_PATH, index=False)
    return plan


if __name__ == "__main__":
    L = coded_design()
    off, counts = design_checks(L)
    print(f"DSD: 변수 {N_CAND_DIM}개 + 가짜 인자 {N_FAKE}개 = {M}열, 실험 {N_RUNS}회")
    print(f"  열 간 상관 최대 {off:.2e} (0 이어야 함), 열마다 (−1, 0, +1) 개수 = {counts[0]}")
    plan = make_plan()
    show = ["run"] + CANDIDATES + [f"fin_gap_{b}" for b in BANKS]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(plan[show].to_string(index=False))
