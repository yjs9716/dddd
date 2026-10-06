"""
V6 설계변수 정의 — 후보 11개, 선별(DSD) 결과에 따라 활성/고정이 나뉜다 (단일 출처)

흐름
  1단계(DSD)  : 후보 11개 전부를 움직인다 → DSD_analysis.py 가 영향 없는 변수를 판정해
               screening_decision.json 에 "고정할 변수와 그 값"을 기록한다.
  2단계(OLHD) : 활성 변수만 OLHD/적응샘플링/GPR 입력으로 쓰고, 고정 변수는
               screening_decision.json 의 값을 매 회차 그대로 SolidWorks에 써넣는다.

좌표 체계
  · 단위 좌표 u ∈ [0,1]^11 : 샘플링(DSD 수준, LHS, Sobol 후보)은 전부 이 좌표에서 한다.
  · 실제 설계값 x           : decode(u). 반올림 + 핀 개수 접어 넣기(V5 OLHD.decode 와 같은 방식,
                              뱅크별로 각자 적용) 때문에 decode 는 역함수가 없다.
  · GPR 입력                : normalize_active(x) = 활성 변수만 박스 정규화.
  고정 변수는 "실제값"이 아니라 "단위 좌표 u"로 고정한다. 핀 개수처럼 다른 변수(두께)에
  따라 허용 범위가 바뀌는 변수도 u 로 고정하면 어떤 두께에서도 항상 만들 수 있는 형상이 된다.

변수 범위는 V5와 같게 두었다(근거는 Code/OLHD.py PARAM_SPEC 주석). 바꾸려면 여기만 고칠 것.
"""
import json
import os

import numpy as np

from fins import max_fin_count, BANK_PARAMS, BANK_SPAN_MM

# ── 후보 설계변수 11개 (이름, 하한, 상한) — 이름은 SolidWorks 전역변수명과 일치해야 함 ──
CANDIDATE_SPEC = [
    ("input_thick",        13.0,  25.0),   # mm — 25 초과 시 첫 발열채널 자리에 핀 배치 불가(간섭 제약)
    ("input_angle",        90.0, 150.0),   # deg
    ("power_input_thick",   3.0,  15.0),   # mm — 상한 20→15: V5 216점에서 15mm 초과는 분기비 60% 이상
                                            #   (74점 전부 요구 범위 밖). 분기비 요구 최대 50%까지
                                            #   열어두기 위한 범위(20~50% 만족점은 3.0~12.4mm).
                                            #   하한 3mm는 V5와 같음(2mm는 메시 해상도상 보류)
    ("mid_thick",          10.0,  25.0),   # mm — input_thick과 같은 이유
    ("mid_angle",          90.0, 140.0),   # deg
    ("mid_input_thick",    10.0,  25.0),   # mm — 위와 동일
    ("output_thick",       13.0,  35.0),   # mm
    ("fin_thick_1",         1.5,   3.0),   # mm — 1차 통과 핀 두께
    ("fin_count_1",        10.0,  21.0),   # 개 — 1차 통과 핀 개수 (두께에 따라 상한이 접힘)
    ("fin_thick_2",         1.5,   3.0),   # mm — 2차 통과 핀 두께
    ("fin_count_2",        10.0,  21.0),   # 개 — 2차 통과 핀 개수
]

# 캠페인 내내 안 바뀌는 값 — SolidWorks 스케치에 숫자로 직접 들어있음(V5와 동일)
FIXED_GEOMETRY = {
    "power_output_thick": 25.0,
    "fin_height":          8.0,
}

CANDIDATES = [p[0] for p in CANDIDATE_SPEC]
C_LO = np.array([p[1] for p in CANDIDATE_SPEC], dtype=float)
C_HI = np.array([p[2] for p in CANDIDATE_SPEC], dtype=float)
N_CAND_DIM = len(CANDIDATES)

INT_PARAMS = ("fin_count_1", "fin_count_2")
# 뱅크별 (두께 인덱스, 개수 인덱스)
BANK_IDX = {b: (CANDIDATES.index(t), CANDIDATES.index(n)) for b, (t, n) in BANK_PARAMS.items()}


def decode(unit):
    """단위 좌표 [0,1]^11 → 실제 설계값 (11개). 뱅크별 갭 제약을 항상 만족한다.

    V5 OLHD.decode()와 같은 규칙을 뱅크마다 적용한다:
      ① 먼저 0.1 단위로 반올림 (허용 핀 개수는 실제로 쓸 두께로 계산해야 하므로)
      ② 핀 개수 = round(N_lo + u·(min(N_hi, N_max(t)) − N_lo))  — 그 두께의 허용 범위로 접어 넣음
    """
    u = np.atleast_2d(np.asarray(unit, dtype=float))
    x = np.round(C_LO + u * (C_HI - C_LO), 1)
    for b, (it, iN) in BANK_IDX.items():
        nmax = np.array([max_fin_count(t, BANK_SPAN_MM[b]) for t in x[:, it]], float)
        n_hi = np.maximum(np.minimum(C_HI[iN], nmax), C_LO[iN])
        x[:, iN] = np.round(C_LO[iN] + u[:, iN] * (n_hi - C_LO[iN]))
    return x[0] if np.ndim(unit) == 1 else x


def to_dict(row, include_fixed_geometry=True):
    """실제 설계값 (11,) → {변수명: 값}. 핀 개수는 int."""
    d = {}
    for name, v in zip(CANDIDATES, row):
        d[name] = int(round(v)) if name in INT_PARAMS else float(v)
    if include_fixed_geometry:
        d.update(FIXED_GEOMETRY)
    return d


# ══════════════ 선별 결과 (2단계에서 사용) ══════════════
class Screening:
    """screening_decision.json 을 읽어 활성/고정 변수를 제공한다.

    active      : 2단계에서 움직이는 변수 이름 목록 (CANDIDATES 순서 유지)
    fixed_u     : {고정 변수명: 단위 좌표 u}  — decode 시 그대로 끼워 넣음
    """

    def __init__(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"선별 결과 파일이 없음: {path}\n"
                "  → DSD 29회를 끝낸 뒤 DSD_analysis.py 를 실행해 screening_decision.json 을 만들 것")
        with open(path, encoding="utf-8") as f:
            dec = json.load(f)
        self.raw = dec
        self.active = [n for n in CANDIDATES if n in dec["active"]]
        self.fixed_u = {n: float(v) for n, v in dec["fixed_u"].items()}
        unknown = set(self.active) | set(self.fixed_u)
        if unknown != set(CANDIDATES) or set(self.active) & set(self.fixed_u):
            raise ValueError("screening_decision.json 의 active/fixed_u 가 후보 11개를 정확히 한 번씩 덮지 않음")
        self.idx_active = np.array([CANDIDATES.index(n) for n in self.active])
        self.lo = C_LO[self.idx_active]
        self.hi = C_HI[self.idx_active]
        self.n_dim = len(self.active)

    def full_unit(self, u_active):
        """활성 변수 단위 좌표 (n, d_a) → 후보 11개 단위 좌표 (n, 11) (고정 변수는 fixed_u)."""
        ua = np.atleast_2d(np.asarray(u_active, dtype=float))
        U = np.empty((len(ua), N_CAND_DIM))
        for name, v in self.fixed_u.items():
            U[:, CANDIDATES.index(name)] = v
        U[:, self.idx_active] = ua
        return U

    def decode_active(self, u_active):
        """활성 변수 단위 좌표 → 실제 설계값 11개."""
        x = decode(self.full_unit(u_active))
        return x[0] if np.ndim(u_active) == 1 else x

    def normalize_active(self, x_full):
        """실제 설계값 11개 (n, 11) → GPR 입력 (활성 변수만 박스 정규화)."""
        x = np.atleast_2d(np.asarray(x_full, dtype=float))
        return (x[:, self.idx_active] - self.lo) / (self.hi - self.lo)

    def fixed_values(self):
        """고정 변수의 실제값 — 핀 개수처럼 두께에 따라 바뀌는 값은 '대표값'(활성 변수 중앙 기준)."""
        x = self.decode_active(np.full(self.n_dim, 0.5))
        return {n: x[CANDIDATES.index(n)] for n in self.fixed_u}
