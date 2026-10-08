"""
V6 — 방열핀 배치 계산 (핀 관련 형상 수식의 단일 출처)

V5(Code/fins.py) 대비 변경점
  ⓪ 최소 갭 2.5 → 2.0mm (아래 MIN_GAP_MM 주석). 두께 1.5mm에서 최대 핀 개수 21 → 24개.
  ① 핀뱅크 2개(1차 통과 / 2차 통과)를 각자의 두께·개수로 계산한다.
     수식 자체는 V5와 같고, 함수가 뱅크 하나의 (두께, 개수)를 받는 구조도 같다.
     뱅크 번호 → 변수명 매핑(BANK_PARAMS)만 새로 둔다.
  ② max_fin_count()의 부동소수점 오차 수정
     V5는 int((L − g_min) // (t + g_min))였는데, t=1.7에서 84/4.2 가 이진수 표현 때문에
     19.999… 로 계산돼 19개를 돌려준다(최소 갭 2.5 기준). 그런데 20개일 때 갭은 정확히 2.5mm라
     is_feasible()은 20개를 허용한다 — 같은 파일 안에서 두 함수가 어긋났다.
     V6는 is_feasible()과 같은 여유(1e-9)를 둬서 두 함수가 항상 일치하게 했다.

배치 규칙 — 등간격 (V5와 동일)
  [벽] g [핀] g [핀] g ... g [핀] g [벽]
  폐합조건 : L = N·t + (N+1)·g   →   g = (L − N·t) / (N+1)
  제약     : g ≥ MIN_GAP_MM   →   N ≤ (L − g_min) / (t + g_min)

⚠ FIN_SPAN_MM(86.5)은 두 뱅크가 같은 길이라는 전제다(V5 형상 기준).
  뱅크 길이가 다르면 BANK_SPAN_MM 을 뱅크별로 바꿀 것.
"""
import math

FIN_SPAN_MM = 86.5          # 핀뱅크 안목 길이 [mm]
MIN_GAP_MM  = 2.0           # 유로 최소 갭 [mm] — V5 2.5 → V6 2.0
#   실험 범위를 밀링 가능 한계 쪽(Ø1.5 롱넥 엔드밀, 깊이 8mm)까지 넓혀 둔 값이다.
#   제작 최소 갭(예: 2.5mm)은 실험이 아니라 최적화 단계의 제약으로 건다 — 그러면
#   "갭을 2.5 → 2.0mm로 줄이면 성능이 얼마나 좋아지는가"를 대리모델로 정량화할 수 있다.
BANK_SPAN_MM = {1: FIN_SPAN_MM, 2: FIN_SPAN_MM}

# 뱅크 번호 → (두께 변수명, 개수 변수명)
BANK_PARAMS = {
    1: ("fin_thick_1", "fin_count_1"),
    2: ("fin_thick_2", "fin_count_2"),
}
BANKS = tuple(BANK_PARAMS)

_EPS = 1e-9


def fin_gap(fin_thick, fin_count, span=FIN_SPAN_MM):
    """등간격 배치일 때의 유로 갭 [mm]."""
    n = int(round(fin_count))
    return (span - n * float(fin_thick)) / (n + 1)


def max_fin_count(fin_thick, span=FIN_SPAN_MM):
    """이 두께에서 갭 제약을 지킬 수 있는 최대 핀 개수 (is_feasible과 같은 여유 적용)."""
    return int((span - MIN_GAP_MM) / (float(fin_thick) + MIN_GAP_MM) + _EPS)


def max_fin_thick(fin_count, span=FIN_SPAN_MM, step=0.1):
    """이 개수에서 갭 제약을 지킬 수 있는 최대 핀 두께 — step(0.1mm) 격자로 내림.
    N·t + (N+1)·g_min ≤ L  →  t ≤ (L − (N+1)·g_min) / N"""
    n = int(round(fin_count))
    t = (span - (n + 1) * MIN_GAP_MM) / n
    return round(math.floor(t / step + _EPS) * step, 10)


def is_feasible(fin_thick, fin_count, span=FIN_SPAN_MM):
    return fin_gap(fin_thick, fin_count, span) >= MIN_GAP_MM - _EPS


def channel_offsets(fin_thick, fin_count, span=FIN_SPAN_MM):
    """유로 N+1개의 (시작 오프셋, 폭) 목록 — 핀뱅크 시작단(벽)에서 잰 거리 [mm]."""
    n = int(round(fin_count))
    g = fin_gap(fin_thick, n, span)
    pitch = g + float(fin_thick)
    return [(k * pitch, g) for k in range(n + 1)]


def bank_values(params, bank):
    """params dict 에서 뱅크 하나의 (두께, 개수) 추출."""
    t_name, n_name = BANK_PARAMS[bank]
    return float(params[t_name]), int(round(params[n_name]))


def bank_gap(params, bank):
    t, n = bank_values(params, bank)
    return fin_gap(t, n, BANK_SPAN_MM[bank])


def bank_feasible(params, bank):
    t, n = bank_values(params, bank)
    return is_feasible(t, n, BANK_SPAN_MM[bank])


def all_banks_feasible(params):
    return all(bank_feasible(params, b) for b in BANKS)


def describe(fin_thick, fin_count, span=FIN_SPAN_MM):
    n = int(round(fin_count))
    g = fin_gap(fin_thick, n, span)
    return (f"핀 {n}개 x t={float(fin_thick):.2f}mm → 갭 {g:.3f}mm "
            f"(유로 {n+1}개, 최소 {MIN_GAP_MM}mm {'OK' if is_feasible(fin_thick, n, span) else '위반'})")


def describe_bank(params, bank):
    t, n = bank_values(params, bank)
    return f"[{bank}차 뱅크] " + describe(t, n, BANK_SPAN_MM[bank])


if __name__ == "__main__":
    print(f"핀뱅크 길이 L = {FIN_SPAN_MM}mm,  최소 갭 = {MIN_GAP_MM}mm\n")
    for k in range(15, 31):
        t = k / 10
        n = max_fin_count(t)
        assert is_feasible(t, n) and not is_feasible(t, n + 1), t
        print(f"  t={t:.1f}mm → N_max={n:2d}  (갭 {fin_gap(t, n):.3f}mm)")
    print("\nmax_fin_count ↔ is_feasible 일치 확인 OK (t=1.5~3.0)")
