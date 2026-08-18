"""
V3 유로 8변수 — Icepak 결과 CSV 파싱

Code(V2)의 result_parser.py 대비 변경점
  - vel_cv_pass1, vel_cv_pass2를 summary 전용 원시값이 아니라 extract_and_save()의
    반환 dict(results)에도 포함시킴 — V3의 ML.py가 vel_cv(=max(cv1,cv2)) 대신
    cv1/cv2를 각각 별도 목적함수로 학습하기 때문에 필요
  - vel_cv, max_temp는 목적함수에서는 빠지지만 참고/로그용으로 계속 반환·기록함
    (수집은 그대로, 무엇을 "목적함수로 쓸지"만 ML.py 쪽에서 다르게 결정)
  - 파싱 로직(CSV 행 위치, CV 계산식 등) 자체는 V2와 동일 — 형상 측정 방식이
    바뀐 게 아니므로 건드릴 이유가 없음

icepak.py(스크립트 리코더 완성본) 기준.
  - 발열채널 19개 → 8개 (source01~08)
  - 핀뱅크 레인: 1차 통과(V_inlet_01~07) + 2차 통과(V_inlet2_01~07) = 14개
    · 두 통과는 분기 때문에 평균 유속 자체가 다르므로 14개를 한 덩어리로 묶어
      CV를 내면 "레인 분배 불균일"과 "통과별 유량 수준 차이"가 뒤섞임
      → 각 통과별로 따로 CV를 내고, V3에서는 그 둘을 각각 목적함수로 사용
        (V2는 나쁜 쪽 max()만 목적함수로 썼음 — max()가 만드는 꺾임이 GPR
        학습을 어렵게 만든다는 게 과거 데이터 재현 분석으로 확인되어 V3에서 분리함)
  - 전원모듈 분기 유량: Icepak의 VolumeFlowRate가 값을 못 내서(면적만 반환),
    법선방향 Speed 면적가중평균 x 면적 으로 환산 (수학적으로 동일한 값).
    면적은 CSV의 실측값(Area/Volume 열)을 씀 — 메시 이산화로 도면값과 어긋날 수 있어서
  - 중량: SolidWorks만으로 계산 (Icepak 불필요)
    · PAO 부피 = FULL_SOLID_VOLUME_MM3(채널 없이 완전히 채워진 형상 부피, 상수)
                 − 알루미늄 부피(SolidWorks, 매 idx 리빌드된 실제 형상)
    · 중량 = 알루미늄 질량 + PAO 부피 x 밀도

CSV 한 장 구조 (skiprows=5, 열 인덱스는 Min=7 / Max=8 / Mean=9 / Stdev=10)
  행 0~7   : source01~08 온도
  행 8     : Fan1_Passage 차압
  행 9~15  : V_inlet_01~07  (1차 통과, +X) 속도
  행 16~22 : V_inlet2_01~07 (2차 통과) 속도
  행 23    : Rectangle1 (전원모듈 분기 입구) 법선방향 속도
"""
import os

import pandas as pd

from OLHD import PARAM_NAMES
from paths import SUMMARY_PATH
from icepak import PAO_DENSITY, N_SOURCE, N_LANE

# 채널이 하나도 안 뚫린, 완전히 채워진 상태의 판재(plate+plate_base) 부피 [mm^3].
#   SolidWorks에서 실측 확정한 상수 (2025-08 기준 형상). PAO 부피 = 이 값 − 알루미늄 부피.
#   ⚠ plate/plate_base의 바깥 치수(둘레) 자체를 바꾸는 형상 변경이 있으면 이 값도 다시 재야 함
#   (8개 설계변수는 내부 유로만 바꾸므로 이 상수엔 영향 없음)
FULL_SOLID_VOLUME_MM3 = 2341073.1

# ── CSV 행 위치 — icepak.py의 Calculation 추가 순서와 1:1 대응 ──
#   개수(N_SOURCE / N_LANE)는 icepak.py에서 import해서 씀 → 거기만 바꾸면 여기가 따라감
ROW_SOURCE = 0                              # 0~7
ROW_DP     = ROW_SOURCE + N_SOURCE          # 8
ROW_LANE1  = ROW_DP + 1                     # 9~15
ROW_LANE2  = ROW_LANE1 + N_LANE             # 16~22
ROW_PMFLOW = ROW_LANE2 + N_LANE             # 23
N_ROWS     = ROW_PMFLOW + 1                 # 24

COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11   # Area/Volume 열 — 모든 Calculation이 Object/Surface라 항상 면적(m^2).
                #   "5.51786e-05 m^2"처럼 단위 문자열이 붙어 나오므로 숫자만 떼어 씀

# Fan1의 FixedVolumetric 설정값 (icepak.py "Volumetric:=" 4ltr_per_min)
TOTAL_FLOW_LPM = 4.0

_SUMMARY_COLS = (["idx"] + PARAM_NAMES
                 + ["pressure_drop", "vel_cv", "temp_std", "max_temp",
                    "power_module_flow", "weight",
                    "vel_cv_pass1", "vel_cv_pass2", "power_module_flow_lpm"])


def _area_m2(cell):
    """Area/Volume 열 파싱 — "5.51786e-05 m^2" → 5.51786e-05"""
    return float(str(cell).strip().split()[0])


def _lane_flow_cv(df, row0):
    """레인 N_LANE개의 '유량' 기준 변동계수 [%] (모집단 std, 엑셀 STDEV.P 기준).

    속도 Mean이 아니라 Mean x Area(= 레인별 유량)로 계산하는 이유:
      Fields Summary는 CAD 면이 아니라 메시에 투영된 면에서 값을 뽑기 때문에,
      측정면이 셀 경계에 딱 안 맞으면 벽면(속도≈0) 셀까지 면적에 포함되는 경우가 있음.
      이때 Mean은 그 0에 가까운 영역까지 평균에 섞여 희석되지만(레인마다 다르게 왜곡됨),
      Mean x Area = ∫v·dA 는 속도 0인 영역이 0을 기여하므로 값이 그대로 보존됨.
      실측에서도 이 방식이 특정 레인만 튀는 현상을 상당 부분 없애는 걸 확인함.

    2차 통과는 유동 방향이 반대라 법선성분이 음수로 잡힐 수 있어 절대값 사용
    (부호가 CV의 부호를 뒤집으면 max 비교가 무의미해지므로).
    """
    speeds = df.iloc[row0:row0 + N_LANE, COL_MEAN].astype(float).abs()
    areas  = df.iloc[row0:row0 + N_LANE, COL_AREA].map(_area_m2)
    flows  = (speeds.values * areas.values)

    mean = float(flows.mean())
    if mean < 1e-15:
        raise ValueError("레인 유량이 0에 가까움 — 측정면 위치/방향벡터 확인 필요")
    return float(flows.std(ddof=0) / mean * 100)


def extract_and_save(idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """
    반환 dict:
      pressure_drop      : 차압                              (목적함수)
      temp_std           : 8채널 온도표준편차                  (목적함수)
      vel_cv_pass1        : 1차 통과 레인 유량 CV               (목적함수)
      vel_cv_pass2        : 2차 통과 레인 유량 CV               (목적함수)
      vel_cv             : max(1차통과 CV, 2차통과 CV)         (참고용 — 목적함수 아님)
      max_temp           : 8채널 최고온도                      (참고용 — 목적함수 아님,
                            방열핀 설계가 지배적이라 이번 유로 변수 스윕 대상에서 제외)
      power_module_flow  : 전원모듈 분기 유량비율 [0~1]         (제약조건용)
      weight             : 알루미늄 + PAO 총 중량 [kg]         (제약조건용)
    """
    # sep=None + engine="python": Icepak Fields Summary export가 콤마/탭 중
    # 어느 쪽으로 나오든 자동 인식 (버전/설정에 따라 다를 수 있어 안전하게 대응)
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

    # ── 핀뱅크 레인 유량 CV (통과별로 따로 → V3는 둘 다 목적함수로 사용) ──
    cv1 = _lane_flow_cv(df, ROW_LANE1)
    cv2 = _lane_flow_cv(df, ROW_LANE2)
    vel_cv = max(cv1, cv2)   # 참고/로그용으로만 유지

    # ── 전원모듈 분기 유량 ──
    #   Q[m^3/s] = 법선방향 속도 면적가중평균 x 단면적
    #   면적가중평균의 정의상 (적분/면적)이므로, 다시 면적을 곱하면 적분값이 그대로 복원됨
    #   면적은 계산(8mm x power_input_thick) 대신 CSV의 실측 면적을 씀 — 메시가 셀
    #   경계로 이산화하면서 도면값과 어긋나는 경우(특히 얇은 두께에서)가 있었기 때문
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
        "vel_cv_pass1":      cv1,
        "vel_cv_pass2":      cv2,
        "vel_cv":            vel_cv,      # 참고용
        "max_temp":          max_temp,    # 참고용
        "power_module_flow": power_module_flow,
        "weight":            weight,
    }

    # ── summary 누적 저장 (사람이 훑어보는 용도 — 통과별 CV 등 원시값도 같이) ──
    if os.path.exists(SUMMARY_PATH):
        try:
            df_summary = pd.read_csv(SUMMARY_PATH)
        except Exception as e:
            # 기존 파일 손상 — results_v3.csv(ML.py 관리)가 같은 데이터를 보관 중이라
            # 요약본은 새로 시작해도 데이터 손실 없음
            print(f"[{idx}] summary_v3.csv 손상 감지({e}) — 새로 시작합니다")
            df_summary = pd.DataFrame(columns=_SUMMARY_COLS)
    else:
        df_summary = pd.DataFrame(columns=_SUMMARY_COLS)

    row = {"idx": idx}
    row.update(params)
    row.update(results)
    row["power_module_flow_lpm"] = pm_lpm
    df_summary = pd.concat([df_summary, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    df_summary.to_csv(SUMMARY_PATH, index=False)

    print(f"[{idx}] 차압:{pressure_drop:.4f}  1차CV:{cv1:.4f}%  2차CV:{cv2:.4f}%  "
          f"온도std:{temp_std:.4f}  최고온도(참고):{max_temp:.2f}  "
          f"전원모듈유량:{pm_lpm:.3f}LPM ({power_module_flow*100:.1f}%)  중량:{weight:.3f}kg")
    return results
