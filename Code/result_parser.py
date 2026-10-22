"""
V5 유로+방열핀 9변수 — Icepak 결과 CSV 파싱

V4(Code3) 대비 핵심 변경점 — 레인을 개별 학습(14개) 대신 통과당 표준편차 1개로 압축
  핀 개수(fin_count)가 설계변수가 되면서 유로 개수가 11~22개로 설계마다 달라진다.
  GPR은 출력 차원이 고정이어야 하므로 개수가 변하는 값을 통째로 목적함수로 쓸 수 없다.

  처음엔 "개수와 무관한 상대위치 몇 점만 골라 재자"(top/mid/bot 등)를 검토했지만,
  그 위치 선정 자체가 애매해지는 문제가 있었다(유로가 짝수개면 정중앙 유로가 없어서
  최대 반 피치까지 어긋남, top/bot 2점만 쓰면 중앙이 볼록/오목한 비단조 패턴을
  놓침). 그래서 위치를 고르는 대신 **유로 전체(N+1개)를 다 재고, 그 값들의
  표준편차 하나로 압축**하는 쪽으로 바꿨다:
      std_pass1 : 1차 통과 유로 전체 유량의 표준편차 [LPM]
      std_pass2 : 2차 통과 유로 전체 유량의 표준편차 [LPM]
  개수와 무관하게 항상 스칼라 하나라 위치 선정 문제도, GPR 차원 문제도 없고,
  전체를 다 재므로 어느 위치의 이상 패턴이든 std에 반영된다(위치 정보 자체는
  잃지만, "얼마나 불균일한가"라는 목적엔 위치보다 이 크기가 더 직접적인 지표다).

  종료판정 주의 ★ std는 CV처럼 설계가 좋아질수록(균일해질수록) 0에 가까워지는
  값이다. 상대오차(%)로 판정하면 CV 때와 똑같이 폭발한다(레인 하나의 절대오차를
  0.01 LPM이라 하면, 표준편차 자체가 0.005 LPM대로 내려간 좋은 설계에서는 상대오차가
  60%까지 치솟는다). 그래서 ML.py는 std_pass1/2를 상대오차가 아니라 **절대오차**
  (오차전파로 유도한 0.003 LPM, SD(std 오차) ≈ eps/√N)로 판정한다.

  개별 유로 원시값은 results_v5.csv에는 안 남긴다 — 매 idx마다 저장되는 원본
  Icepak CSV(result_000.csv 등)에 이미 다 있어서 나중에 필요하면 그걸 보면 된다.

V4에서 그대로 유지하는 것
  · 속도 Mean이 아니라 Mean x Area(= ∫v·dA)로 유량을 계산한다(_lane_flows_lpm 참고).
  · 면적 파싱, 중량 계산 방식.

CSV 한 장 구조 (skiprows=5, 열 인덱스는 Min=7 / Max=8 / Mean=9 / Stdev=10)
  n = fin_count + 1 (이번 설계의 유로 개수 — 설계마다 다름)
  행 0~8             : source01~09 온도
  행 9               : Fan1_Passage 차압
  행 10~(10+n-1)     : V_inlet_00~(n-1)   (1차 통과, +X) 속도
  행 (10+n)~(10+2n-1): V_inlet2_00~(n-1)  (2차 통과) 속도
  행 (10+2n)         : Rectangle1 (전원모듈 분기 입구) 법선방향 속도
"""
import numpy as np
import pandas as pd

from fins import fin_gap
from icepak import PAO_DENSITY, N_SOURCE

# 채널이 하나도 안 뚫린, 완전히 채워진 상태의 판재(plate+plate_base) 부피 [mm^3].
#   PAO 부피 = 이 값 − 알루미늄 부피.
#   ⚠ V5 확인 필요: 이 상수는 판재 바깥 치수로 결정된다. V5에서 핀뱅크 길이가
#     66.5 → 86.5mm로 늘어났다면 판재 외형도 바뀌었을 가능성이 크므로 SolidWorks에서
#     다시 실측할 것. (핀 자체는 유로 안쪽이라 이 값에 영향 없음 — 핀이 차지하는
#     부피는 알루미늄 부피에 이미 반영되어 SolidWorks가 알려준다)
FULL_SOLID_VOLUME_MM3 = 2341073.1

# ── CSV 행 위치 — icepak.py의 Calculation 추가 순서와 1:1 대응 ──
#   유로 개수(n)가 설계마다 달라지므로 고정 상수가 아니라 함수로 계산한다.
ROW_SOURCE = 0                                # 0~8
ROW_DP     = ROW_SOURCE + N_SOURCE            # 9
ROW_LANE1  = ROW_DP + 1                       # 10 ~ (10+n-1)


def _row_layout(n_channels):
    """유로 개수(n_channels)에 따른 행 위치 (lane2 시작행, pmflow행, 전체 행수)."""
    row_lane2  = ROW_LANE1 + n_channels
    row_pmflow = row_lane2 + n_channels
    n_rows     = row_pmflow + 1
    return row_lane2, row_pmflow, n_rows


COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11   # Area/Volume 열 — "5.51786e-05 m^2"처럼 단위 문자열이 붙어 나옴

# Fan1의 FixedVolumetric 설정값 (icepak.py "Volumetric:=" 4ltr_per_min)
TOTAL_FLOW_LPM = 4.0

# ── ML.py가 목적함수로 쓰는 이름 ──
STD_NAMES = ["std_pass1", "std_pass2"]


def _area_m2(cell):
    """Area/Volume 열 파싱 — "5.51786e-05 m^2" → 5.51786e-05"""
    return float(str(cell).strip().split()[0])


def _lane_flows_lpm(df, row0, n_channels):
    """유로 n_channels개의 유량 [L/min] 배열을 반환.

    속도 Mean이 아니라 Mean x Area(= 레인별 유량)로 계산하는 이유:
      Fields Summary는 CAD 면이 아니라 메시에 투영된 면에서 값을 뽑기 때문에,
      측정면이 셀 경계에 딱 안 맞으면 벽면(속도≈0) 셀까지 면적에 포함되는 경우가 있음.
      이때 Mean은 그 0에 가까운 영역까지 평균에 섞여 희석되지만(레인마다 다르게 왜곡됨),
      Mean x Area = ∫v·dA 는 속도 0인 영역이 0을 기여하므로 값이 그대로 보존됨.
      ⚠ V5에서는 갭이 최소 2.5mm까지 좁아지므로 이 왜곡이 V4보다 커진다.
        메시가 갭을 최소 2~3셀로 분할하는지 첫 실행에서 반드시 확인할 것.

    2차 통과는 유동 방향이 반대라 법선성분이 음수로 잡힐 수 있어 절대값 사용.
    """
    return np.abs(_lane_flows_signed(df, row0, n_channels))


def _lane_flows_signed(df, row0, n_channels):
    """부호를 살린 레인 유량 [L/min] — 역류 여부 진단용."""
    speeds = df.iloc[row0:row0 + n_channels, COL_MEAN].astype(float).values
    areas  = df.iloc[row0:row0 + n_channels, COL_AREA].map(_area_m2).values
    return speeds * areas * 60000.0          # m^3/s → L/min


def _check_closure(idx, flows1, flows2):
    """측정면이 엉뚱한 데 놓였는지 확인 — 유로 전체를 다 재므로 강한 검산이 가능하다.

    V4처럼 sum(flows) ≈ 총유량이 그대로 성립한다(V4는 레인 7개가 곧 전체 유로였고,
    V5도 이번엔 다시 전체를 재므로 동일). 배수 수준으로 어긋날 때만 경고한다.
    """
    for tag, flows in (("1차", flows1), ("2차", flows2)):
        total = float(np.sum(flows))
        ratio = total / TOTAL_FLOW_LPM
        if not (0.7 <= ratio <= 1.3):
            print(f"  ⚠ [{idx}] {tag} 통과 유량 검산 이상: 유로 합계 {total:.3f} LPM "
                  f"(총유량 {TOTAL_FLOW_LPM} LPM의 {ratio*100:.0f}%). "
                  f"측정면 위치/개수를 확인할 것")


def extract_and_save(idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """
    반환 dict:
      std_pass1/std_pass2 : 통과별 유로 전체 유량의 표준편차 [LPM] (목적함수 — GPR 학습 대상)
      pressure_drop        : 차압                              (목적함수)
      temp_std             : 9채널 온도표준편차                 (목적함수)
      max_temp             : 9채널 최고온도                     (목적함수)
      power_module_flow    : 전원모듈 분기 유량비율 [0~1]       (제약조건용)
      weight               : 알루미늄 + PAO 총 중량 [kg]        (제약조건용)
      fin_gap              : 이번 설계의 유로 갭 [mm]           (기록용 — 종속변수)
    """
    n_channels = int(round(params["fin_count"])) + 1
    row_lane2, row_pmflow, n_rows = _row_layout(n_channels)

    # sep=None + engine="python": Icepak Fields Summary export가 콤마/탭 중
    # 어느 쪽으로 나오든 자동 인식
    df = pd.read_csv(result_path, header=None, skiprows=5, sep=None, engine="python",
                     on_bad_lines="skip")

    if len(df) < n_rows:
        raise ValueError(
            f"CSV 행이 {len(df)}개뿐 — {n_rows}개 기대(유로 {n_channels}개 기준).\n"
            "  icepak.py의 Calculation 개수/순서가 바뀌었거나, params['fin_count']가 "
            "이 설계를 만들 때 쓴 값과 다르거나, Fan1_Passage 같은 항목이 "
            "계산되지 않았는지 확인할 것"
        )

    # ── 온도 (9채널) ──
    temp_rows = df.iloc[ROW_SOURCE:ROW_SOURCE + N_SOURCE]
    max_temp  = float(temp_rows[COL_MAX].astype(float).max())
    temp_std  = float(temp_rows[COL_MEAN].astype(float).std(ddof=0))

    # ── 차압 ──
    pressure_drop = float(df.iloc[ROW_DP, COL_MEAN])

    # ── 레인별 유량 (유로 전체 n개 x 2통과) ──
    flows1 = _lane_flows_lpm(df, ROW_LANE1, n_channels)
    flows2 = _lane_flows_lpm(df, row_lane2, n_channels)

    # 역류 진단: 2차 통과에서 부호가 섞이면 abs()가 실제 분배를 가릴 수 있음
    signed2 = _lane_flows_signed(df, row_lane2, n_channels)
    if np.ptp(np.sign(signed2)) > 1 and np.abs(signed2).min() > 1e-6:
        print(f"  ⚠ [{idx}] 2차 통과 레인 부호가 섞임(일부 역류 의심): "
              f"{np.round(signed2, 4).tolist()}")

    _check_closure(idx, flows1, flows2)

    std_pass1 = float(flows1.std(ddof=0))
    std_pass2 = float(flows2.std(ddof=0))

    # ── 전원모듈 분기 유량 ──
    #   Q[m^3/s] = 법선방향 속도 면적가중평균 x 단면적
    #   면적은 계산(8mm x power_input_thick) 대신 CSV의 실측 면적을 씀 — 메시 이산화로
    #   도면값과 어긋나는 경우(특히 얇은 두께에서)가 있었기 때문
    pm_speed = abs(float(df.iloc[row_pmflow, COL_MEAN]))
    pm_area  = _area_m2(df.iloc[row_pmflow, COL_AREA])
    pm_lpm   = pm_speed * pm_area * 60000.0          # m^3/s → L/min
    power_module_flow = pm_lpm / TOTAL_FLOW_LPM      # 총유량 대비 비율 (0~1)

    # ── 중량 (알루미늄 + 유로를 채운 PAO) — Icepak 없이 SolidWorks 값만으로 계산 ──
    pao_volume_mm3 = FULL_SOLID_VOLUME_MM3 - float(aluminum_volume_mm3)
    if pao_volume_mm3 <= 0:
        raise ValueError(
            f"PAO 부피가 0 이하({pao_volume_mm3:.1f} mm^3) — "
            "알루미늄 부피가 FULL_SOLID_VOLUME_MM3보다 큼. 상수가 최신 형상과 안 맞을 수 있음"
        )
    pao_mass_kg = pao_volume_mm3 * 1e-9 * PAO_DENSITY
    weight = float(aluminum_mass_kg) + pao_mass_kg

    gap = fin_gap(params["fin_thick"], params["fin_count"])

    results = {
        "pressure_drop":     pressure_drop,
        "temp_std":          temp_std,
        "max_temp":          max_temp,
        "std_pass1":         std_pass1,
        "std_pass2":         std_pass2,
        "power_module_flow": power_module_flow,
        "weight":            weight,
        "fin_gap":           gap,        # 종속변수 기록용
    }

    print(f"[{idx}] 차압:{pressure_drop:.4f}  1차std:{std_pass1:.5f}LPM  "
          f"2차std:{std_pass2:.5f}LPM  온도std:{temp_std:.4f}  최고온도:{max_temp:.2f}  "
          f"전원모듈유량:{pm_lpm:.3f}LPM ({power_module_flow*100:.1f}%)  중량:{weight:.3f}kg")
    print(f"      핀 {int(round(params['fin_count']))}개(유로 {n_channels}개) "
          f"x t={params['fin_thick']:.2f}mm → 갭 {gap:.3f}mm")
    print(f"      1차 레인유량[LPM] 합계={flows1.sum():.4f} "
          f"min={flows1.min():.4f} max={flows1.max():.4f}")
    print(f"      2차 레인유량[LPM] 합계={flows2.sum():.4f} "
          f"min={flows2.min():.4f} max={flows2.max():.4f}")
    return results
