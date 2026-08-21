"""
V4 유로 8변수 — Icepak 결과 CSV 파싱 (레인별 유량을 압축하지 않고 그대로 반환)

V3(Code2/result_parser.py) 대비 핵심 변경점
  레인 유량 14개를 CV로 압축하지 않고, 개별 유량을 그대로 반환·저장한다.

  왜 바꾸는가 — CV는 "증폭기"이기 때문
    CV = std(레인 7개 유량) / mean(레인 7개 유량)
    좋은 설계일수록 7개 유량이 거의 같아지는데, 그러면 분자(표준편차)가
    "거의 같은 수들의 차이"가 되어 원래 값의 작은 오차가 크게 벌어진다.
    실제로 계산해보면(레인 유량을 1% 오차로 맞혔다고 가정):

        진짜 CV  2% → CV 오차 16.7%
        진짜 CV  5% → CV 오차  6.0%
        진짜 CV 10% → CV 오차  2.9%
        진짜 CV 15% → CV 오차  1.9%

    즉 CV를 1% 이내로 예측하려면 레인 유량을 0.1% 이내로 맞혀야 하는데,
    그건 메시를 다시 자르는 것만으로도 흔들리는 수준이라 CFD 자체가 못 주는 정밀도다.
    V2에서 364점, V3에서 139점을 돌리고도 예측오차 1% 기준을 한 번도 못 넘은 건
    데이터가 부족해서가 아니라 애초에 도달 불가능한 목표였기 때문.

    → 레인 유량 자체는 형상에 따라 매끄럽게 변하는 정상적인 물리량이라
      GPR이 잘 배우고, 1% 기준도 현실적이다. CV는 그 예측값들로부터 계산해서
      GA 입력·사람이 보는 지표로 계속 쓴다(지표가 없어지는 게 아니라,
      "무엇을 학습할지"만 한 단계 아래로 내리는 것).

    이건 V2→V3에서 max(cv1,cv2)를 cv1/cv2로 쪼갠 것과 같은 논리의 연장이다.
    합쳐진 값은 배우기 어렵고, 쪼갠 값은 배우기 쉽다.

  그 외(행 위치, 면적 파싱, 중량 계산 등)는 V3와 동일 — 형상 측정 방식이
  바뀐 게 아니므로 건드릴 이유가 없음. icepak.py도 손대지 않았다
  (Fields Summary가 이미 레인 14개 값을 전부 내보내고 있었고, V3의 파서가
   그걸 CV로 압축해 버리고 있었을 뿐).

CSV 한 장 구조 (skiprows=5, 열 인덱스는 Min=7 / Max=8 / Mean=9 / Stdev=10)
  행 0~7   : source01~08 온도
  행 8     : Fan1_Passage 차압
  행 9~15  : V_inlet_01~07  (1차 통과, +X) 속도
  행 16~22 : V_inlet2_01~07 (2차 통과) 속도
  행 23    : Rectangle1 (전원모듈 분기 입구) 법선방향 속도
"""
import numpy as np
import pandas as pd

from OLHD import PARAM_NAMES
from icepak import PAO_DENSITY, N_SOURCE, N_LANE

# 채널이 하나도 안 뚫린, 완전히 채워진 상태의 판재(plate+plate_base) 부피 [mm^3].
#   SolidWorks에서 실측 확정한 상수 (2025-08 기준 형상). PAO 부피 = 이 값 − 알루미늄 부피.
#   ⚠ plate/plate_base의 바깥 치수(둘레) 자체를 바꾸는 형상 변경이 있으면 이 값도 다시 재야 함
FULL_SOLID_VOLUME_MM3 = 2341073.1

# ── CSV 행 위치 — icepak.py의 Calculation 추가 순서와 1:1 대응 ──
ROW_SOURCE = 0                              # 0~7
ROW_DP     = ROW_SOURCE + N_SOURCE          # 8
ROW_LANE1  = ROW_DP + 1                     # 9~15
ROW_LANE2  = ROW_LANE1 + N_LANE             # 16~22
ROW_PMFLOW = ROW_LANE2 + N_LANE             # 23
N_ROWS     = ROW_PMFLOW + 1                 # 24

COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11   # Area/Volume 열 — "5.51786e-05 m^2"처럼 단위 문자열이 붙어 나옴

# Fan1의 FixedVolumetric 설정값 (icepak.py "Volumetric:=" 4ltr_per_min)
TOTAL_FLOW_LPM = 4.0

# ── 레인별 유량 이름 (ML.py가 이 이름들을 그대로 목적함수로 씀) ──
#    단위는 L/min — 사람이 읽기 쉽고, 총유량 4 LPM과 바로 비교되므로
LANE1_NAMES = [f"lane1_{i+1:02d}" for i in range(N_LANE)]   # 1차 통과 7개
LANE2_NAMES = [f"lane2_{i+1:02d}" for i in range(N_LANE)]   # 2차 통과 7개
LANE_NAMES  = LANE1_NAMES + LANE2_NAMES                     # 총 14개


def _area_m2(cell):
    """Area/Volume 열 파싱 — "5.51786e-05 m^2" → 5.51786e-05"""
    return float(str(cell).strip().split()[0])


def _lane_flows_lpm(df, row0):
    """레인 N_LANE개의 유량 [L/min] 배열을 반환.

    속도 Mean이 아니라 Mean x Area(= 레인별 유량)로 계산하는 이유:
      Fields Summary는 CAD 면이 아니라 메시에 투영된 면에서 값을 뽑기 때문에,
      측정면이 셀 경계에 딱 안 맞으면 벽면(속도≈0) 셀까지 면적에 포함되는 경우가 있음.
      이때 Mean은 그 0에 가까운 영역까지 평균에 섞여 희석되지만(레인마다 다르게 왜곡됨),
      Mean x Area = ∫v·dA 는 속도 0인 영역이 0을 기여하므로 값이 그대로 보존됨.

    2차 통과는 유동 방향이 반대라 법선성분이 음수로 잡힐 수 있어 절대값 사용.
      ⚠ 만약 어떤 설계에서 '일부 레인만 역류'하면 abs()가 그 부호를 지워버려
        실제와 다른 분배로 보이게 된다. 레인별 원시 부호를 확인하고 싶으면
        _lane_flows_signed()를 쓸 것 (아래).
    """
    return np.abs(_lane_flows_signed(df, row0))


def _lane_flows_signed(df, row0):
    """부호를 살린 레인 유량 [L/min] — 역류 여부 진단용."""
    speeds = df.iloc[row0:row0 + N_LANE, COL_MEAN].astype(float).values
    areas  = df.iloc[row0:row0 + N_LANE, COL_AREA].map(_area_m2).values
    return speeds * areas * 60000.0          # m^3/s → L/min


def _cv_from_flows(flows):
    """유량 배열 → 변동계수 [%] (모집단 std, 엑셀 STDEV.P 기준).

    ML.py가 GPR 예측값으로부터 CV를 계산할 때도 이 함수를 쓴다
    (실측 CV와 예측 CV가 정확히 같은 식으로 계산되도록 단일 출처로 유지).
    """
    flows = np.asarray(flows, dtype=float)
    mean = float(flows.mean())
    if mean < 1e-15:
        raise ValueError("레인 유량이 0에 가까움 — 측정면 위치/방향벡터 확인 필요")
    return float(flows.std(ddof=0) / mean * 100)


def extract_and_save(idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """
    반환 dict:
      lane1_01 ~ lane1_07 : 1차 통과 레인별 유량 [L/min]   (목적함수 — GPR 학습 대상)
      lane2_01 ~ lane2_07 : 2차 통과 레인별 유량 [L/min]   (목적함수 — GPR 학습 대상)
      pressure_drop       : 차압                            (목적함수)
      temp_std            : 8채널 온도표준편차               (목적함수)
      max_temp            : 8채널 최고온도                   (목적함수)
      vel_cv_pass1/pass2  : 레인 유량 CV [%]                (참고·GA용 — 학습 대상 아님)
      vel_cv              : max(cv1, cv2)                   (참고용)
      power_module_flow   : 전원모듈 분기 유량비율 [0~1]     (제약조건용)
      weight              : 알루미늄 + PAO 총 중량 [kg]      (제약조건용)
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

    # ── 레인별 유량 (V4의 핵심 — 압축하지 않고 14개를 그대로 보존) ──
    flows1 = _lane_flows_lpm(df, ROW_LANE1)
    flows2 = _lane_flows_lpm(df, ROW_LANE2)

    # 역류 진단: 2차 통과에서 부호가 섞이면 abs()가 실제 분배를 가릴 수 있음
    signed2 = _lane_flows_signed(df, ROW_LANE2)
    if np.sign(signed2).ptp() > 1 and np.abs(signed2).min() > 1e-6:
        print(f"  ⚠ [{idx}] 2차 통과 레인 부호가 섞임(일부 역류 의심): "
              f"{np.round(signed2, 4).tolist()}")

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

    results = {
        "pressure_drop":     pressure_drop,
        "temp_std":          temp_std,
        "max_temp":          max_temp,
        "power_module_flow": power_module_flow,
        "weight":            weight,
        "vel_cv_pass1":      cv1,        # 참고·GA용 (학습 대상 아님)
        "vel_cv_pass2":      cv2,        # 참고·GA용
        "vel_cv":            vel_cv,     # 참고용
    }
    results.update({n: float(v) for n, v in zip(LANE1_NAMES, flows1)})
    results.update({n: float(v) for n, v in zip(LANE2_NAMES, flows2)})

    print(f"[{idx}] 차압:{pressure_drop:.4f}  1차CV:{cv1:.4f}%  2차CV:{cv2:.4f}%  "
          f"온도std:{temp_std:.4f}  최고온도:{max_temp:.2f}  "
          f"전원모듈유량:{pm_lpm:.3f}LPM ({power_module_flow*100:.1f}%)  중량:{weight:.3f}kg")
    print(f"      1차 레인유량[LPM]: {np.round(flows1, 4).tolist()}")
    print(f"      2차 레인유량[LPM]: {np.round(flows2, 4).tolist()}")
    return results
