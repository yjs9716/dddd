"""
V6 — Icepak 결과 CSV 파싱 (V5 Code/result_parser.py 기반)

V5 대비 변경점
  · 1차·2차 통과의 유로 개수가 다르다: n1 = fin_count_1 + 1, n2 = fin_count_2 + 1.
    행 구조가 아래처럼 바뀐다(icepak.py 의 Calculation 추가 순서와 1:1 대응):
      행 0~8                 : source01~09 온도
      행 9                   : Fan1_Passage 차압
      행 10 ~ 10+n1−1        : V_inlet_00~(n1−1)   (1차 통과)
      행 10+n1 ~ 10+n1+n2−1  : V_inlet2_00~(n2−1)  (2차 통과)
      행 10+n1+n2            : Rectangle1 (전원모듈 분기 입구)
  · 결과에 뱅크별 갭(fin_gap_1, fin_gap_2)을 기록한다.

그대로 유지 (근거는 V5 주석): Mean×Area 유량, 통과별 유로 유량 표준편차(std_pass1/2),
전원모듈 분기 유량비, 중량 = 알루미늄(SolidWorks) + PAO(전체 부피 − 알루미늄 부피).
"""
import numpy as np
import pandas as pd

from fins import BANKS, bank_values, bank_gap
from icepak import PAO_DENSITY, N_SOURCE
from responses import STD_NAMES  # noqa: F401  (V5와 같은 이름으로 다른 모듈이 참조)

# ⚠ 판재 외형이 V5와 같다는 전제의 값 — 형상을 바꿨다면 SolidWorks에서 다시 실측할 것
FULL_SOLID_VOLUME_MM3 = 2341073.1

ROW_SOURCE = 0
ROW_DP     = ROW_SOURCE + N_SOURCE    # 9
ROW_LANE1  = ROW_DP + 1               # 10

COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11

TOTAL_FLOW_LPM = 4.0


def _row_layout(n1, n2):
    row_lane2  = ROW_LANE1 + n1
    row_pmflow = row_lane2 + n2
    return row_lane2, row_pmflow, row_pmflow + 1


def _area_m2(cell):
    return float(str(cell).strip().split()[0])


def _lane_flows_signed(df, row0, n_channels):
    speeds = df.iloc[row0:row0 + n_channels, COL_MEAN].astype(float).values
    areas  = df.iloc[row0:row0 + n_channels, COL_AREA].map(_area_m2).values
    return speeds * areas * 60000.0


def _lane_flows_lpm(df, row0, n_channels):
    return np.abs(_lane_flows_signed(df, row0, n_channels))


def _check_closure(tag_idx, flows1, flows2, power_module_flow):
    """측정면 유로 유량 합계가 그 패스에 흘러야 할 유량과 맞는지 검산 (경고만, 결과값 무관).
    1차 통과는 입구 유량 전부(4 LPM), 2차 통과는 분기 후 남은 4·(1 − 분기비)가 기준."""
    expected = {"1차": TOTAL_FLOW_LPM, "2차": TOTAL_FLOW_LPM * (1.0 - power_module_flow)}
    for tag, flows in (("1차", flows1), ("2차", flows2)):
        ratio = float(np.sum(flows)) / expected[tag]
        if not (0.7 <= ratio <= 1.3):
            print(f"  ⚠ [{tag_idx}] {tag} 통과 유량 검산 이상: 유로 합계 {np.sum(flows):.3f} LPM "
                  f"(기대값 {expected[tag]:.3f} LPM의 {ratio*100:.0f}%). 측정면 위치/개수를 확인할 것")


def extract_and_save(tag_idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """반환 dict: pressure_drop, temp_std, max_temp, std_pass1, std_pass2,
    power_module_flow(0~1), weight(kg), fin_gap_1, fin_gap_2"""
    n1 = bank_values(params, 1)[1] + 1
    n2 = bank_values(params, 2)[1] + 1
    row_lane2, row_pmflow, n_rows = _row_layout(n1, n2)

    df = pd.read_csv(result_path, header=None, skiprows=5, sep=None, engine="python",
                     on_bad_lines="skip")
    if len(df) < n_rows:
        raise ValueError(
            f"CSV 행이 {len(df)}개뿐 — {n_rows}개 기대(유로 1차 {n1}개 / 2차 {n2}개 기준).\n"
            "  icepak.py 의 Calculation 순서, 또는 params 의 fin_count_1/2 가 이 설계와 같은지 확인할 것")

    temp_rows = df.iloc[ROW_SOURCE:ROW_SOURCE + N_SOURCE]
    max_temp = float(temp_rows[COL_MAX].astype(float).max())
    temp_std = float(temp_rows[COL_MEAN].astype(float).std(ddof=0))
    pressure_drop = float(df.iloc[ROW_DP, COL_MEAN])

    flows1 = _lane_flows_lpm(df, ROW_LANE1, n1)
    flows2 = _lane_flows_lpm(df, row_lane2, n2)
    signed2 = _lane_flows_signed(df, row_lane2, n2)
    if np.ptp(np.sign(signed2)) > 1 and np.abs(signed2).min() > 1e-6:
        print(f"  ⚠ [{tag_idx}] 2차 통과 레인 부호가 섞임(일부 역류 의심): {np.round(signed2, 4).tolist()}")

    pm_speed = abs(float(df.iloc[row_pmflow, COL_MEAN]))
    pm_area = _area_m2(df.iloc[row_pmflow, COL_AREA])
    pm_lpm = pm_speed * pm_area * 60000.0
    power_module_flow = pm_lpm / TOTAL_FLOW_LPM
    _check_closure(tag_idx, flows1, flows2, power_module_flow)

    pao_volume_mm3 = FULL_SOLID_VOLUME_MM3 - float(aluminum_volume_mm3)
    if pao_volume_mm3 <= 0:
        raise ValueError(f"PAO 부피가 0 이하({pao_volume_mm3:.1f} mm^3) — FULL_SOLID_VOLUME_MM3 확인")
    weight = float(aluminum_mass_kg) + pao_volume_mm3 * 1e-9 * PAO_DENSITY

    results = {
        "pressure_drop": pressure_drop,
        "temp_std": temp_std,
        "max_temp": max_temp,
        "std_pass1": float(flows1.std(ddof=0)),
        "std_pass2": float(flows2.std(ddof=0)),
        "power_module_flow": power_module_flow,
        "weight": weight,
        # 기록 전용 (responses.RECORD_ONLY) — CV = std_pass / mean_pass 사후 계산용
        "mean_pass1": float(flows1.mean()),
        "mean_pass2": float(flows2.mean()),
    }
    results.update({f"fin_gap_{b}": bank_gap(params, b) for b in BANKS})

    print(f"[{tag_idx}] 차압:{pressure_drop:.4f}  1차std:{results['std_pass1']:.5f}LPM  "
          f"2차std:{results['std_pass2']:.5f}LPM  온도std:{temp_std:.4f}  최고온도:{max_temp:.2f}  "
          f"전원모듈유량:{pm_lpm:.3f}LPM ({power_module_flow*100:.1f}%)  중량:{weight:.3f}kg")
    print(f"      1차 유로 {n1}개 합계={flows1.sum():.4f}  /  2차 유로 {n2}개 합계={flows2.sum():.4f} LPM")
    return results
