"""
V5 유로+방열핀 10변수 — Icepak 결과 CSV 파싱

V4(Code3) 대비 핵심 변경점 — 레인 측정을 14개(통과당 7개)에서 6개(통과당 3개)로
  왜 줄이는가: 핀 개수(fin_count)가 설계변수가 되면서 유로 개수가 11~22개로
  설계마다 달라진다. 이때 "몇 번째 유로"라는 인덱스는 설계마다 다른 물리적 위치를
  가리키게 되고, 무엇보다 GPR은 출력 차원이 고정이어야 해서 개수가 변하는 값을
  통째로 목적함수로 쓸 수가 없다.

  그래서 유로 개수와 무관하게 항상 같은 의미를 갖는 상대위치 3점만 측정한다:
      top : 최상단 유로 (상단벽 바로 다음)
      mid : 중앙 유로
      bot : 최하단 유로 (하단벽 바로 앞)
  측정면의 실제 좌표는 fins.measure_channels()가 fin_thick/fin_count로부터 계산한다
  (icepak.py가 그 값으로 측정 사각형을 배치함).

  잃는 것: "중간의 특정 유로 하나만 막힘" 같은 비단조 편차는 못 본다.
  다만 헤더 분배 유동의 지배적 실패모드는 위→아래 단조 편중이나 중앙 vs 양끝
  포물선이라 3점이면 주된 패턴은 잡힌다. 유로 개수가 가변인 이상 "전체 측정"은
  선택지 자체가 없으므로, 손해라기보다 불가피한 근사다.

V4에서 그대로 유지하는 것
  · 레인 유량을 CV로 압축하지 않고 개별 유량을 그대로 학습 대상으로 둔다.
    CV는 "거의 같은 수들의 차이"라 작은 오차를 크게 증폭시킨다(레인을 1% 오차로
    맞혀도 진짜 CV가 2%면 CV 오차는 16.7%). V2 364점·V3 139점을 돌리고도 1% 기준을
    한 번도 못 넘은 진짜 이유였다. CV는 예측된 레인 유량으로부터 계산해서 GA 입력과
    사람이 보는 지표로만 계속 쓴다.
  · 속도 Mean이 아니라 Mean x Area(= ∫v·dA)로 유량을 계산한다(_lane_flows_lpm 참고).
  · 면적 파싱, 중량 계산 방식.

CSV 한 장 구조 (skiprows=5, 열 인덱스는 Min=7 / Max=8 / Mean=9 / Stdev=10)
  행 0~7   : source01~08 온도
  행 8     : Fan1_Passage 차압
  행 9~11  : V_inlet_top/mid/bot   (1차 통과, +X) 속도
  행 12~14 : V_inlet2_top/mid/bot  (2차 통과) 속도
  행 15    : Rectangle1 (전원모듈 분기 입구) 법선방향 속도
"""
import numpy as np
import pandas as pd

from fins import MEASURE_LABELS, N_MEASURE, fin_gap
from icepak import PAO_DENSITY, N_SOURCE

# 채널이 하나도 안 뚫린, 완전히 채워진 상태의 판재(plate+plate_base) 부피 [mm^3].
#   PAO 부피 = 이 값 − 알루미늄 부피.
#   ⚠ V5 확인 필요: 이 상수는 판재 바깥 치수로 결정된다. V5에서 핀뱅크 길이가
#     66.5 → 86.5mm로 늘어났다면 판재 외형도 바뀌었을 가능성이 크므로 SolidWorks에서
#     다시 실측할 것. (핀 자체는 유로 안쪽이라 이 값에 영향 없음 — 핀이 차지하는
#     부피는 알루미늄 부피에 이미 반영되어 SolidWorks가 알려준다)
FULL_SOLID_VOLUME_MM3 = 2341073.1

# ── CSV 행 위치 — icepak.py의 Calculation 추가 순서와 1:1 대응 ──
ROW_SOURCE = 0                                # 0~7
ROW_DP     = ROW_SOURCE + N_SOURCE            # 8
ROW_LANE1  = ROW_DP + 1                       # 9~11
ROW_LANE2  = ROW_LANE1 + N_MEASURE            # 12~14
ROW_PMFLOW = ROW_LANE2 + N_MEASURE            # 15
N_ROWS     = ROW_PMFLOW + 1                   # 16

COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11   # Area/Volume 열 — "5.51786e-05 m^2"처럼 단위 문자열이 붙어 나옴

# Fan1의 FixedVolumetric 설정값 (icepak.py "Volumetric:=" 4ltr_per_min)
TOTAL_FLOW_LPM = 4.0

# ── 레인별 유량 이름 (ML.py가 이 이름들을 그대로 목적함수로 씀) ──
#    단위는 L/min — 사람이 읽기 쉽고, 총유량 4 LPM과 바로 비교되므로
LANE1_NAMES = [f"lane1_{lab}" for lab in MEASURE_LABELS]   # 1차 통과 3개
LANE2_NAMES = [f"lane2_{lab}" for lab in MEASURE_LABELS]   # 2차 통과 3개
LANE_NAMES  = LANE1_NAMES + LANE2_NAMES                    # 총 6개


def _area_m2(cell):
    """Area/Volume 열 파싱 — "5.51786e-05 m^2" → 5.51786e-05"""
    return float(str(cell).strip().split()[0])


def _lane_flows_lpm(df, row0):
    """측정 유로 N_MEASURE개의 유량 [L/min] 배열을 반환.

    속도 Mean이 아니라 Mean x Area(= 레인별 유량)로 계산하는 이유:
      Fields Summary는 CAD 면이 아니라 메시에 투영된 면에서 값을 뽑기 때문에,
      측정면이 셀 경계에 딱 안 맞으면 벽면(속도≈0) 셀까지 면적에 포함되는 경우가 있음.
      이때 Mean은 그 0에 가까운 영역까지 평균에 섞여 희석되지만(레인마다 다르게 왜곡됨),
      Mean x Area = ∫v·dA 는 속도 0인 영역이 0을 기여하므로 값이 그대로 보존됨.
      ⚠ V5에서는 갭이 최소 2.5mm까지 좁아지므로 이 왜곡이 V4보다 커진다.
        메시가 갭을 최소 2~3셀로 분할하는지 첫 실행에서 반드시 확인할 것.

    2차 통과는 유동 방향이 반대라 법선성분이 음수로 잡힐 수 있어 절대값 사용.
    """
    return np.abs(_lane_flows_signed(df, row0))


def _lane_flows_signed(df, row0):
    """부호를 살린 레인 유량 [L/min] — 역류 여부 진단용."""
    speeds = df.iloc[row0:row0 + N_MEASURE, COL_MEAN].astype(float).values
    areas  = df.iloc[row0:row0 + N_MEASURE, COL_AREA].map(_area_m2).values
    return speeds * areas * 60000.0          # m^3/s → L/min


def _cv_from_flows(flows):
    """유량 배열 → 변동계수 [%] (모집단 std, 엑셀 STDEV.P 기준).

    ML.py가 GPR 예측값으로부터 CV를 계산할 때도 이 함수를 쓴다
    (실측 CV와 예측 CV가 정확히 같은 식으로 계산되도록 단일 출처로 유지).

    ⚠ V5에서는 표본이 7개가 아니라 3개(top/mid/bot)다. 전체 유로의 CV가 아니라
      "상·중·하 3점 사이의 편차"를 보는 지표로 의미가 바뀌었다. 참고·GA용으로만 쓰고
      절대값을 V4와 직접 비교하지 말 것.
    """
    flows = np.asarray(flows, dtype=float)
    mean = float(flows.mean())
    if mean < 1e-15:
        raise ValueError("레인 유량이 0에 가까움 — 측정면 위치/방향벡터 확인 필요")
    return float(flows.std(ddof=0) / mean * 100)


def _check_closure(idx, flows1, flows2, params):
    """측정면이 엉뚱한 데 놓였는지 대략 확인.

    V4에서는 레인 7개가 곧 전체 유로라 sum(flows) ≈ 4 LPM 이라는 강한 검산이 됐지만,
    V5는 유로 N+1개 중 3개만 재므로 그 검산을 못 쓴다. 대신 근사 검산을 한다:

        측정 3점의 평균유량 x 유로개수 ≈ 총유량

    3점이 전체를 대표한다는 가정이라 정확히 맞을 리는 없다(애초에 그 편차를 보려고
    재는 것이므로). 그래서 배수 수준으로 크게 어긋날 때만 경고한다 — 측정면이 유로가
    아닌 곳에 놓였거나, 갭 계산과 실제 형상이 어긋난 경우를 잡기 위한 것.
    """
    n_ch = int(round(params["fin_count"])) + 1
    for tag, flows in (("1차", flows1), ("2차", flows2)):
        est = float(np.mean(flows)) * n_ch
        ratio = est / TOTAL_FLOW_LPM
        if not (0.5 <= ratio <= 2.0):
            print(f"  ⚠ [{idx}] {tag} 통과 유량 검산 이상: 측정평균 x 유로 {n_ch}개 "
                  f"= {est:.3f} LPM (총유량 {TOTAL_FLOW_LPM} LPM의 {ratio*100:.0f}%). "
                  f"측정면 위치/갭 계산을 확인할 것")


def extract_and_save(idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """
    반환 dict:
      lane1_top/mid/bot   : 1차 통과 측정 유로 유량 [L/min]   (목적함수 — GPR 학습 대상)
      lane2_top/mid/bot   : 2차 통과 측정 유로 유량 [L/min]   (목적함수 — GPR 학습 대상)
      pressure_drop       : 차압                              (목적함수)
      temp_std            : 8채널 온도표준편차                 (목적함수)
      max_temp            : 8채널 최고온도                     (목적함수)
      vel_cv_pass1/pass2  : 측정 3점의 CV [%]                 (참고·GA용 — 학습 대상 아님)
      vel_cv              : max(cv1, cv2)                     (참고용)
      power_module_flow   : 전원모듈 분기 유량비율 [0~1]       (제약조건용)
      weight              : 알루미늄 + PAO 총 중량 [kg]        (제약조건용)
      fin_gap             : 이번 설계의 유로 갭 [mm]           (기록용 — 종속변수)
    """
    # sep=None + engine="python": Icepak Fields Summary export가 콤마/탭 중
    # 어느 쪽으로 나오든 자동 인식
    df = pd.read_csv(result_path, header=None, skiprows=5, sep=None, engine="python",
                     on_bad_lines="skip")

    if len(df) < N_ROWS:
        raise ValueError(
            f"CSV 행이 {len(df)}개뿐 — {N_ROWS}개 기대.\n"
            "  icepak.py의 Calculation 개수/순서가 바뀌었거나 "
            "Fan1_Passage 같은 항목이 계산되지 않았는지 확인할 것"
        )

    # ── 온도 (8채널) ──
    temp_rows = df.iloc[ROW_SOURCE:ROW_SOURCE + N_SOURCE]
    max_temp  = float(temp_rows[COL_MAX].astype(float).max())
    temp_std  = float(temp_rows[COL_MEAN].astype(float).std(ddof=0))

    # ── 차압 ──
    pressure_drop = float(df.iloc[ROW_DP, COL_MEAN])

    # ── 레인별 유량 (측정 3점 x 2통과) ──
    flows1 = _lane_flows_lpm(df, ROW_LANE1)
    flows2 = _lane_flows_lpm(df, ROW_LANE2)

    # 역류 진단: 2차 통과에서 부호가 섞이면 abs()가 실제 분배를 가릴 수 있음
    signed2 = _lane_flows_signed(df, ROW_LANE2)
    if np.ptp(np.sign(signed2)) > 1 and np.abs(signed2).min() > 1e-6:
        print(f"  ⚠ [{idx}] 2차 통과 레인 부호가 섞임(일부 역류 의심): "
              f"{np.round(signed2, 4).tolist()}")

    _check_closure(idx, flows1, flows2, params)

    cv1    = _cv_from_flows(flows1)
    cv2    = _cv_from_flows(flows2)
    vel_cv = max(cv1, cv2)   # 참고/로그용

    # ── 전원모듈 분기 유량 ──
    #   Q[m^3/s] = 법선방향 속도 면적가중평균 x 단면적
    #   면적은 계산(8mm x power_input_thick) 대신 CSV의 실측 면적을 씀 — 메시 이산화로
    #   도면값과 어긋나는 경우(특히 얇은 두께에서)가 있었기 때문
    pm_speed = abs(float(df.iloc[ROW_PMFLOW, COL_MEAN]))
    pm_area  = _area_m2(df.iloc[ROW_PMFLOW, COL_AREA])
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
        "power_module_flow": power_module_flow,
        "weight":            weight,
        "vel_cv_pass1":      cv1,        # 참고·GA용 (학습 대상 아님)
        "vel_cv_pass2":      cv2,        # 참고·GA용
        "vel_cv":            vel_cv,     # 참고용
        "fin_gap":           gap,        # 종속변수 기록용
    }
    results.update({n: float(v) for n, v in zip(LANE1_NAMES, flows1)})
    results.update({n: float(v) for n, v in zip(LANE2_NAMES, flows2)})

    print(f"[{idx}] 차압:{pressure_drop:.4f}  1차CV:{cv1:.4f}%  2차CV:{cv2:.4f}%  "
          f"온도std:{temp_std:.4f}  최고온도:{max_temp:.2f}  "
          f"전원모듈유량:{pm_lpm:.3f}LPM ({power_module_flow*100:.1f}%)  중량:{weight:.3f}kg")
    print(f"      핀 {int(round(params['fin_count']))}개 x t={params['fin_thick']:.2f}mm "
          f"x h={params['fin_height']:.2f}mm → 갭 {gap:.3f}mm")
    print(f"      1차 레인유량[LPM] {dict(zip(MEASURE_LABELS, np.round(flows1, 4)))}")
    print(f"      2차 레인유량[LPM] {dict(zip(MEASURE_LABELS, np.round(flows2, 4)))}")
    return results
