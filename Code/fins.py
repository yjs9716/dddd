"""
V5 — 방열핀 배치 계산 (핀 관련 형상 수식의 단일 출처)

이 파일이 필요한 이유
  V5에서 핀두께(fin_thick)·핀개수(fin_count)·핀높이(fin_height)가 설계변수가 되면서,
  "유로 갭이 몇 mm인가", "몇 번째 유로가 어디에 있는가"가 설계마다 달라진다.
  이 계산이 OLHD(샘플링) / ML(적응샘플링·GA) / icepak(측정면 배치) 세 곳에서 각각
  필요한데, 수식이 흩어지면 한 곳만 고쳤을 때 조용히 어긋난다.
  그래서 핀 배치에 관한 모든 수식을 여기 한 곳에만 둔다.

배치 규칙 — 등간격
  [벽] g [핀] g [핀] g ... g [핀] g [벽]
  핀 N개 → 유로(갭) N+1개. 모든 갭이 같은 값 g다.
  즉 "최상단 핀과 상단벽 사이", "핀과 핀 사이", "최하단 핀과 하단벽 사이"가
  전부 동일한 g가 된다 — 따로 맞출 필요 없이 아래 폐합식에서 자동으로 그렇게 된다.

  폐합조건 : L = N·t + (N+1)·g
  → 갭     : g = (L − N·t) / (N+1)

  가변피치(등차수열)도 검토했으나 구현 복잡도 대비 이득이 불확실해서 등간격으로 확정함.
  대신 핀 개수 N을 설계변수로 올려서 배치 밀도를 탐색한다.

제약조건
  g >= MIN_GAP_MM : 갭이 너무 좁으면 유로가 막히고 메시도 못 자른다.
    N에 대해 풀면 N <= (L − g_min) / (t + g_min) — max_fin_count()가 이 값이다.
    ⚠ 이 제약 때문에 (t, N) 박스의 약 30%가 무효 영역이다. 그래서 OLHD/적응샘플링은
      박스에서 뽑고 버리는 게 아니라, 애초에 유효 영역 안에서만 뽑는다(OLHD.py 참고).

⚠ 형상 상수 확인 필요
  FIN_SPAN_MM(86.5)은 사용자가 지정한 신규 형상 기준값이다. 참고로 V4(Code3) 형상을
  역산하면 L=66.5mm였다(핀 6개, t=2.5, g=7.357142857, 피치 9.857142857 — 위 폐합식과
  정확히 일치함). 즉 V5는 핀뱅크 길이가 66.5 → 86.5로 늘어난 형상을 전제한다.
  SolidWorks 모델이 실제로 86.5mm인지 반드시 대조할 것.
"""

# ── 핀뱅크 형상 상수 ──────────────────────────────────────────
#   핀이 배치되는 구간의 전체 길이 [mm] (양쪽 벽 사이 안목치수)
FIN_SPAN_MM = 86.5

#   유로 최소 갭 [mm] — 이보다 좁은 설계는 아예 실험하지 않는다
MIN_GAP_MM = 2.5


def fin_gap(fin_thick, fin_count):
    """등간격 배치일 때의 유로 갭 [mm].

    g = (L − N·t) / (N+1)
    핀 사이 갭과 양쪽 벽쪽 갭이 전부 이 값으로 같다.
    """
    n = int(round(fin_count))
    return (FIN_SPAN_MM - n * float(fin_thick)) / (n + 1)


def max_fin_count(fin_thick):
    """이 핀두께에서 갭 제약(g >= MIN_GAP_MM)을 지킬 수 있는 최대 핀 개수.

    g = (L − N·t)/(N+1) >= g_min
      → L − N·t >= g_min·N + g_min
      → L − g_min >= N·(t + g_min)
      → N <= (L − g_min) / (t + g_min)
    """
    return int((FIN_SPAN_MM - MIN_GAP_MM) // (float(fin_thick) + MIN_GAP_MM))


def is_feasible(fin_thick, fin_count):
    """갭 제약을 만족하는 (두께, 개수) 조합인가.

    부동소수점 오차로 경계값(예: t=1.5, N=21 → 갭이 정확히 2.5)이 탈락하지 않도록
    아주 작은 여유(1e-9)를 둔다.
    """
    return fin_gap(fin_thick, fin_count) >= MIN_GAP_MM - 1e-9


def channel_offsets(fin_thick, fin_count):
    """유로 N+1개의 (시작 오프셋, 폭) 목록 — 핀뱅크 시작단(벽)에서 잰 거리 [mm].

    k번째 유로(0부터)의 시작 = k·(g + t),  폭 = g
      k=0        : 상단벽 바로 다음 유로
      k=fin_count: 하단벽 바로 앞 유로

    검산: 마지막 유로 끝 = N·(g+t) + g = N·g + N·t + g = (N+1)·g + N·t = L ✓
    """
    n = int(round(fin_count))
    g = fin_gap(fin_thick, n)
    pitch = g + float(fin_thick)
    return [(k * pitch, g) for k in range(n + 1)]


# ── 측정 위치 ─────────────────────────────────────────────────
#   핀 개수가 설계마다 달라지므로 "몇 번째 유로"라는 인덱스는 설계마다 다른 물리적
#   위치를 가리킨다. 게다가 GPR은 출력 차원이 고정이어야 해서 유로 전체(N+1개)를
#   목적함수로 쓸 수도 없다. 그래서 개수와 무관하게 항상 같은 의미를 갖는
#   상대위치 3점(최상단 / 중앙 / 최하단)만 측정한다.
#
#   트레이드오프: "중간의 특정 유로 하나만 막힘" 같은 비단조 편차는 놓친다.
#   다만 헤더 분배 유동의 지배적 실패모드는 위→아래 단조 편중이나 중앙 vs 양끝
#   포물선 형태라, 3점이면 그 주된 패턴은 잡힌다. N이 가변인 이상 "전체 측정"은
#   선택지 자체가 없으므로 이건 손해라기보다 불가피한 근사다.
MEASURE_LABELS = ("top", "mid", "bot")
N_MEASURE = len(MEASURE_LABELS)


def measure_indices(fin_count):
    """측정할 유로 인덱스 3개 (최상단, 중앙, 최하단).

    유로는 0 ~ N번(총 N+1개)이므로 중앙은 N//2.
    (N이 홀수면 정확히 중앙이 아니라 반 칸 위 — 유로 개수가 짝수라 중앙 칸이
     없기 때문이며, 위치가 설계마다 튀지 않고 일관되면 되므로 문제되지 않음)
    """
    n = int(round(fin_count))
    return (0, n // 2, n)


def measure_channels(fin_thick, fin_count):
    """측정 유로 3개의 (라벨, 시작 오프셋 [mm], 폭 [mm]) 목록."""
    offs = channel_offsets(fin_thick, fin_count)
    return [(label, offs[k][0], offs[k][1])
            for label, k in zip(MEASURE_LABELS, measure_indices(fin_count))]


def describe(fin_thick, fin_count):
    """사람이 읽는 한 줄 요약 — 로그용."""
    n = int(round(fin_count))
    g = fin_gap(fin_thick, n)
    return (f"핀 {n}개 x t={float(fin_thick):.2f}mm → 갭 {g:.3f}mm "
            f"(유로 {n+1}개, 최소 {MIN_GAP_MM}mm {'OK' if is_feasible(fin_thick, n) else '위반'})")


if __name__ == "__main__":
    print(f"핀뱅크 길이 L = {FIN_SPAN_MM}mm,  최소 갭 = {MIN_GAP_MM}mm\n")

    print("두께별 최대 핀 개수:")
    for t in (1.5, 2.0, 2.5, 3.0):
        n_max = max_fin_count(t)
        print(f"  t={t:.1f}mm → N_max={n_max:2d}  (그때 갭 {fin_gap(t, n_max):.3f}mm)")

    print("\n갭 표 [mm] (행=두께, 열=핀개수, '-'=제약 위반):")
    counts = list(range(10, 22))
    print("       " + "".join(f"{n:7d}" for n in counts))
    for t in (1.5, 2.0, 2.5, 3.0):
        row = f"  {t:.1f}  "
        for n in counts:
            row += f"{fin_gap(t, n):7.2f}" if is_feasible(t, n) else "      -"
        print(row)

    print("\n검산 (폐합조건 L = N·t + (N+1)·g):")
    for t, n in ((1.5, 21), (1.5, 10), (3.0, 15)):
        offs = channel_offsets(t, n)
        end = offs[-1][0] + offs[-1][1]
        print(f"  t={t}, N={n:2d} → 마지막 유로 끝 {end:.6f}mm  (L={FIN_SPAN_MM}) "
              f"{'OK' if abs(end - FIN_SPAN_MM) < 1e-9 else '불일치!'}")
        print(f"      {describe(t, n)}")
        print(f"      측정유로: " + ", ".join(
            f"{lab}@{off:.2f}~{off+w:.2f}mm" for lab, off, w in measure_channels(t, n)))
