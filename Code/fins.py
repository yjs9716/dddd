"""
V5 — 방열핀 배치 계산 (핀 관련 형상 수식의 단일 출처)

이 파일이 필요한 이유
  V5에서 핀두께(fin_thick)·핀개수(fin_count)가 설계변수가 되면서,
  "유로 갭이 몇 mm인가", "몇 번째 유로가 어디에 있는가"가 설계마다 달라진다.
  이 계산이 OLHD(샘플링) / ML(적응샘플링·GA) / icepak(측정면 배치) 세 곳에서 각각
  필요한데, 수식이 흩어지면 한 곳만 고쳤을 때 조용히 어긋난다.
  그래서 핀 배치에 관한 모든 수식을 여기 한 곳에만 둔다.

  핀높이(fin_height)는 설계변수가 아니라 8.0mm 고정값이다(OLHD.FIXED_PARAMS) —
  유로 깊이(icepak.CHANNEL_DEPTH_MM)와 정확히 같아서 핀 위 우회공간이 아예 없다.
  이유는 두 가지: ① 우회공간이 있으면 그 얇은 틈(설계마다 0.1~2mm로 가변)을
  DOE 전체(90~100점)에서 매번 잘 메싱해야 하는데 실패 시 오염이 데이터 전체에
  조용히 깔린다 ② 우회유동은 핀 표면에 안 닿고 새는 유량이라 압력강하는 낮추고
  열전달은 나쁘게 만드는 트레이드오프라, 캠페인 목적(상대비교)엔 없는 게 더 깨끗한
  신호를 준다. 실제 제작 시엔 브레이징 조립공차 때문에 핀이 유로보다 살짝
  낮아야 하므로(예: 7.5mm), 최종 후보 결정 후 그 값으로 1회 재해석해서
  스펙을 여전히 만족하는지 확인한다 — 캠페인 자체에는 반영하지 않는다.

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


# ── 측정 ──────────────────────────────────────────────────────
#   핀 개수가 설계마다 달라지므로 "몇 번째 유로"라는 인덱스는 설계마다 다른 물리적
#   위치를 가리킨다. 상대위치로 몇 점만 골라 재는 방식(top/mid/bot 등)은 그 위치
#   선정 자체가 애매해지는 문제(짝수 유로에서 정중앙이 없음 등)가 있어서 폐기했다.
#   대신 유로 전체(N+1개)를 다 재고, GPR에는 그 값들의 표준편차(std)만 학습시킨다
#   — std는 개수와 무관하게 항상 스칼라 하나라 차원 문제도, 위치 선정 문제도 없다.
#   (result_parser.py가 표준편차를 계산, ML.py가 std_pass1/std_pass2를 학습)
#   channel_offsets()가 이미 전체 유로 위치를 다 계산해주므로, icepak.py는 그걸
#   그대로 순회하며 측정면을 만들면 된다.


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
        print(f"      유로 {len(offs)}개 전부 측정: " + ", ".join(
            f"{off:.2f}~{off+w:.2f}" for off, w in offs[:3]) + " ...")
