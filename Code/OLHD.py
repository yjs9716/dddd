"""
V5 유로+방열핀 9변수 Optimal Latin Hypercube Design

V4(Code3) 대비 변경점
  ① power_output_thick 제거 → 25mm 고정 (FIXED_PARAMS)
     V4 데이터 211점으로 partial dependence를 뽑아보니, 이 변수는 15~40mm 전 구간에서
     목적함수들이 서로 다른 값을 원하지 않았다(= 트레이드오프가 없다):
         pressure_drop 40mm 선호(변화폭 0.91%) / vel_cv_pass1 40mm(1.41%)
         vel_cv_pass2  40mm 선호(15.19%)        / temp_std 15mm(1.90%) / max_temp 15mm(0.17%)
     40mm 쪽 이득이 크고 반대편 손해는 무시할 수준이라, 최적화가 고민할 게 없는
     "이미 결정이 끝난 변수"였다. 탐색에서 빼고 그 예산을 신규 핀 변수로 돌린다.
     값을 상한 40이 아니라 25로 잡은 건 형상 미관상의 판단(성능차는 위 표대로 미미함).

     ⚠ output_thick은 그대로 자유변수로 둔다. 이쪽도 방향은 안 갈리지만(35mm 선호)
       pressure_drop 전체 변동의 14.5%를 담당할 만큼 영향이 크고, 실측에서 두꺼울수록
       유량이 더 균일해지는(직관과 반대 방향) 거동이 나와 원인이 확정되지 않았다.
       확실치 않은 걸 고정해 버리면 그 구간을 영영 못 보므로 남겨둔다.

  ② 방열핀 2변수 신규 — fin_thick / fin_count (fin_height는 고정값, 아래 ④)
     핀 배치는 등간격이고, 갭은 두께·개수로부터 종속 계산된다(fins.py).
     fin_count는 정수 변수라 GPR/LHD의 연속 좌표를 정수로 반올림해서 쓴다.

  ③ 갭 제약을 샘플링 단계에서 구조적으로 보장
     g = (L − N·t)/(N+1) >= 2.5mm 라는 제약 때문에 (fin_thick, fin_count) 박스의
     약 30%가 무효 영역이다(예: t=3.0에서는 N이 15까지만 가능). 박스에서 뽑고
     버리는 방식(rejection)은 그만큼 후보를 낭비하고 LHD의 층화도 깨진다.
     그래서 fin_count를 "그 두께에서 허용되는 범위" 안으로 접어 넣는 중첩
     샘플링(decode 참고)을 쓴다 — 무효점이 원천적으로 안 나온다.

  ④ fin_height도 자유변수가 아니라 8.0mm 고정 (FIXED_PARAMS)
     원래는 6.0~7.9mm 자유변수였다. 유로 깊이(icepak.CHANNEL_DEPTH_MM)가 8mm로
     고정이라, fin_height가 8보다 작으면 핀 위에 우회공간(0.1~2mm, 설계마다 가변)이
     생기는데, 이 얇고 폭이 계속 바뀌는 틈을 DOE 90~100점 전체에서 매번 제대로
     메싱해야 해서 실패 시 데이터 전체가 조용히 오염될 위험이 크다. 게다가 우회유동은
     핀 표면에 안 닿고 새는 유량이라 압력강하는 낮추고 열전달은 나쁘게 하는
     트레이드오프까지 낀다 — 캠페인 목적(설계 간 상대비교)엔 없는 게 더 깨끗하다.
     그래서 fin_height=8.0(=유로 깊이, 우회공간 0)으로 고정해 이 문제 자체를
     캠페인에서 제거한다. PAO는 solid를 뺀 나머지로 생성되므로(Boolean) 접촉면
     애매함 없이 깔끔하게 처리된다.
     실제 제작 시엔 브레이징 조립공차 때문에 핀이 유로보다 살짝 낮아야 하므로
     (V4에서 쓰던 값 7.5mm), 최종 후보 확정 후 그 값으로 1회 재해석해서 스펙을
     여전히 만족하는지 확인한다 — 캠페인 자체에는 반영하지 않는다.
"""
import numpy as np
from scipy.stats import qmc

from fins import max_fin_count, fin_gap, is_feasible, describe

# ── 자유 설계변수 정의 (이름, 하한, 상한) ────────────────────────
#    이름은 SolidWorks 글로벌 변수명과 반드시 일치해야 함
PARAM_SPEC = [
    ("input_thick",        15.0, 35.0),   # mm
    ("input_angle",        90.0, 150.0),  # deg
    ("power_input_thick",   3.0, 20.0),   # mm — 2mm는 메시 해상도상 보류, 3mm는 로컬 메시로 대응
    ("mid_thick",          15.0, 35.0),   # mm
    ("mid_angle",          90.0, 140.0),  # deg
    ("mid_input_thick",    15.0, 35.0),   # mm
    ("output_thick",       15.0, 35.0),   # mm
    ("fin_thick",           1.5,  3.0),   # mm — 신규(방열핀 두께)
    ("fin_count",          10.0, 21.0),   # 개 — 신규(방열핀 개수, 정수로 반올림해서 씀)
]

# ── 고정 파라미터 (탐색하지 않지만 SolidWorks에는 넣어줘야 하는 값) ──
FIXED_PARAMS = {
    "power_output_thick": 25.0,   # mm — 위 ① 참고
    "fin_height":          8.0,   # mm — 위 ④ 참고, 유로 깊이와 동일(우회공간 없음)
}

PARAM_NAMES = [p[0] for p in PARAM_SPEC]
LO = np.array([p[1] for p in PARAM_SPEC], dtype=float)
HI = np.array([p[2] for p in PARAM_SPEC], dtype=float)
N_DIM = len(PARAM_SPEC)

# 정수로 취급할 변수 — 반올림 대상
INT_PARAMS = ("fin_count",)

I_FIN_THICK = PARAM_NAMES.index("fin_thick")
I_FIN_COUNT = PARAM_NAMES.index("fin_count")

# 기본 DOE 점 수 — "10 x 변수수" 경험칙. 변수를 추가/삭제하면 자동으로 따라감.
#   9변수 → 90점. V4(8변수/80점)보다 10점 늘어난다.
DEFAULT_N_DOE = 10 * N_DIM

# maxmin 탐색 후보 LHD 개수 — 차원이 8→9로 늘어 한 번에 좋은 배치가 잘 안 나옴
N_MAXMIN_TRIALS = 20000


def decode(unit):
    """정규화 좌표 [0,1]^N_DIM → 실제 설계값. 갭 제약을 항상 만족하도록 보장한다.

    핵심은 fin_count를 박스 상한(21)이 아니라 "그 fin_thick에서 허용되는 상한"으로
    접어 넣는 것(중첩 샘플링):

        N_max(t) = (L − g_min) / (t + g_min)          ← fins.max_fin_count()
        N        = round(N_lo + u · (min(N_hi, N_max(t)) − N_lo))

    이렇게 하면 무효 조합이 아예 생성되지 않는다. 대신 fin_thick이 두꺼울수록
    fin_count의 유효 범위가 좁아지므로 두 변수는 서로 독립이 아니게 되는데,
    이건 실제 제약이 만든 삼각형 모양 유효영역을 그대로 반영한 것이라 정상이다.

    unit : (n, N_DIM) 또는 (N_DIM,) 배열
    반환 : 같은 모양의 실제 설계값 배열 (소수점 첫째자리 반올림, fin_count는 정수)
    """
    u = np.atleast_2d(np.asarray(unit, dtype=float))
    x = qmc.scale(u, LO, HI)

    # ⚠ 반올림을 먼저 한다. 허용 핀 개수는 "실제로 쓸 두께"로 계산해야 하기 때문.
    #   반올림 뒤에 계산하지 않으면 이런 사고가 난다:
    #     원값 t=2.1554 → max_fin_count=18 → N=18 선택 → 그 다음 t가 2.2로 반올림
    #     → 실제 갭 (86.5 − 18x2.2)/19 = 2.468mm < 2.5mm  (제약 위반)
    #   두께를 올림 반올림하면 허용 개수가 줄어드는데, 그 전에 개수를 정해버린 탓이다.
    x = np.round(x, 1)

    t = x[:, I_FIN_THICK]
    n_max_geom = np.array([max_fin_count(tv) for tv in t], dtype=float)
    n_hi_eff = np.minimum(HI[I_FIN_COUNT], n_max_geom)
    n_lo = LO[I_FIN_COUNT]
    # 두께가 극단적으로 두꺼워 하한(10개)조차 못 넣는 경우는 이 변수범위에선 생기지
    # 않지만(t=3.0에서도 N_max=15), 범위를 넓힐 때를 대비해 방어적으로 처리
    n_hi_eff = np.maximum(n_hi_eff, n_lo)
    x[:, I_FIN_COUNT] = np.round(n_lo + u[:, I_FIN_COUNT] * (n_hi_eff - n_lo))

    return x[0] if np.ndim(unit) == 1 else x


def normalize(x):
    """실제 설계값 → 박스 정규화 좌표 [0,1]^N_DIM (GPR 입력용).

    decode()의 역함수가 아니다 — decode는 fin_count를 접어 넣으므로 정보가 일부
    소실된다. GPR은 "실제 설계값이 박스 어디에 있나"만 알면 되므로 이쪽을 쓴다.
    """
    return (np.asarray(x, dtype=float) - LO) / (HI - LO)


def generate_olhd(n_samples=DEFAULT_N_DOE, seed=42):
    """
    Optimal Latin Hypercube Design (9변수, 갭 제약 반영)

    N_MAXMIN_TRIALS개의 LHD 후보를 만들어 그중 "점 사이 최소거리가 가장 큰"
    배치를 고른다. 거리는 decode 후 박스 정규화 공간에서 잰다 — fin_count 접힘과
    반올림까지 반영된 실제 배치가 얼마나 고르게 퍼졌는지를 봐야 하기 때문.

    반환: (n_samples, N_DIM) 실제 설계값 배열. 모든 행이 갭 제약을 만족한다.
    """
    from scipy.spatial.distance import pdist

    best_x, best_mindist = None, -np.inf
    for s in range(N_MAXMIN_TRIALS):
        u = qmc.LatinHypercube(d=N_DIM, seed=seed + s).random(n=n_samples)
        x = decode(u)
        md = pdist(normalize(x)).min()
        if md > best_mindist:
            best_mindist, best_x = md, x

    bad = [i for i, r in enumerate(best_x)
           if not is_feasible(r[I_FIN_THICK], r[I_FIN_COUNT])]
    if bad:   # decode가 보장하므로 정상적으로는 안 걸림 — 회귀 방지용 안전망
        raise RuntimeError(f"갭 제약 위반 샘플이 생성됨(decode 버그): 행 {bad}")

    return best_x


def to_dict(row, include_fixed=True):
    """(N_DIM,) 배열 → {변수명: 값} 딕셔너리.

    include_fixed=True면 고정 파라미터(power_output_thick 등)도 함께 넣는다 —
    SolidWorks에는 고정값도 넣어줘야 하기 때문. 결과 CSV에는 자유변수만 기록한다.
    """
    d = {}
    for name, v in zip(PARAM_NAMES, row):
        d[name] = int(round(v)) if name in INT_PARAMS else float(v)
    if include_fixed:
        d.update(FIXED_PARAMS)
    return d


if __name__ == "__main__":
    import time

    t0 = time.time()
    samples = generate_olhd(seed=42)
    print(f"OLHD 샘플 {len(samples)}점 ({N_DIM}변수), 생성 {time.time()-t0:.1f}초\n")

    print("  " + "".join(f"{n:>18s}" for n in PARAM_NAMES) + f"{'gap':>10s}")
    for i, row in enumerate(samples):
        gap = fin_gap(row[I_FIN_THICK], row[I_FIN_COUNT])
        cells = "".join(f"{v:18.1f}" for v in row)
        print(f"{i:3d}: {cells}{gap:10.3f}")

    gaps = np.array([fin_gap(r[I_FIN_THICK], r[I_FIN_COUNT]) for r in samples])
    counts = samples[:, I_FIN_COUNT].astype(int)
    print(f"\n갭   : 최소 {gaps.min():.3f}mm / 중앙 {np.median(gaps):.3f}mm / 최대 {gaps.max():.3f}mm")
    print(f"핀개수: {counts.min()}~{counts.max()}개 "
          f"(분포: {np.bincount(counts, minlength=22)[10:22].tolist()} @10~21개)")
    print(f"제약 위반: {sum(not is_feasible(r[I_FIN_THICK], r[I_FIN_COUNT]) for r in samples)}건")
