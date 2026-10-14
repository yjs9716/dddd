"""
V6 — Icepak 결과 CSV 파싱 (V5 Code/result_parser.py 기반)

V5 대비 변경점
  · 1차·2차 통과의 유로 개수가 다르다: n1 = fin_count_1 + 1, n2 = fin_count_2 + 1.
    행 구조가 아래처럼 바뀐다(icepak.py 의 Calculation 추가 순서와 1:1 대응, S = N_SOURCE):
      행 0 ~ S−1               : source01~ 온도 (S = 17, DSD 29회는 9)
      행 S                     : Fan1_Passage 차압
      행 S+1 ~ S+n1            : V_inlet_00~(n1−1)   (1차 통과)
      행 S+1+n1 ~ S+n1+n2      : V_inlet2_00~(n2−1)  (2차 통과)
      행 S+1+n1+n2             : Rectangle1 (전원모듈 분기 입구)
      행 S+1+n1+n2+1           : T_pass1 온도 (1차 통과 후 PAO, OLHD부터)
      행 S+1+n1+n2+2           : Opening1 온도 (출구 PAO, OLHD부터)
  · 결과에 뱅크별 갭(fin_gap_1, fin_gap_2)을 기록한다.
  · (OLHD부터) 분기비 power_module_flow = 분기 유량 ÷ (분기 유량 + 2차 통과 유로 합계).
    단면(Mean×Area) 유량은 벽 쪽 굵은 z 셀에서 속도가 0으로 보간돼 작게 잡힌다 — 1차 통과 유로
    합계가 4 LPM이 아니라 평균 3.3 LPM(V6 110점). 그래서 분기 유량을 4 LPM으로 나누면 분기비가
    작게 나온다(시험 설계: 57% vs 온도 섞임·에너지 보존으로 구한 79%). 같은 방식으로 잰 두 유량의
    비로 정규화하면 공통 편향이 상쇄된다(시험 설계 76.5%). 4 LPM으로 나눈 기존 값은
    power_module_flow_raw 로 남긴다. DSD 29회의 power_module_flow 는 기존(÷4 LPM) 방식이다.
  · (OLHD부터) T_pass1, T_outlet 을 기록하고 열수지를 점검한다(경고만):
      분기 전 흡열 = ρ·c_p·Q·(T_pass1 − 입구),  ρ·c_p·Q·(T_outlet − 입구) ≈ 발열 합계
    분기 후 흡열(= 발열 합계 − 분기 전 흡열)로 전원모듈 필요 분기비를 최적화 단계에서 계산한다.

그대로 유지 (근거는 V5 주석): Mean×Area 유량, 통과별 유로 유량 표준편차(std_pass1/2),
전원모듈 분기 유량비, 중량 = 알루미늄(SolidWorks) + PAO(전체 부피 − 알루미늄 부피).
"""
import numpy as np
import pandas as pd

from fins import BANKS, bank_values, bank_gap
from icepak import PAO_DENSITY, PAO_SPECIFIC_HEAT, INLET_TEMP_C, SOURCE_POWER_W, N_SOURCE
from responses import STD_NAMES  # noqa: F401  (V5와 같은 이름으로 다른 모듈이 참조)

# ⚠ 판재 외형이 V5와 같다는 전제의 값 — 형상을 바꿨다면 SolidWorks에서 다시 실측할 것
FULL_SOLID_VOLUME_MM3 = 2341073.1

ROW_SOURCE = 0
ROW_DP     = ROW_SOURCE + N_SOURCE
ROW_LANE1  = ROW_DP + 1

COL_MAX  = 8
COL_MEAN = 9
COL_AREA = 11

TOTAL_FLOW_LPM = 4.0
# 4 LPM 전체를 1 °C 올리는 데 드는 열 [W/K] (≈117.5)
HEAT_CAPACITY_W_PER_K = PAO_DENSITY * PAO_SPECIFIC_HEAT * TOTAL_FLOW_LPM / 60000.0
TOTAL_HEAT_W = N_SOURCE * SOURCE_POWER_W     # 17 × 40 = 680 W (DSD 29회는 9 × 40 = 360 W)
HEAT_BALANCE_TOL = 0.05                     # 출구 열수지 허용 오차 (경고 기준)


def _row_layout(n1, n2):
    row_lane2  = ROW_LANE1 + n1
    row_pmflow = row_lane2 + n2
    row_t1     = row_pmflow + 1
    row_out    = row_pmflow + 2
    return row_lane2, row_pmflow, row_t1, row_out, row_out + 1


def _area_m2(cell):
    return float(str(cell).strip().split()[0])


def _lane_flows_signed(df, row0, n_channels):
    speeds = df.iloc[row0:row0 + n_channels, COL_MEAN].astype(float).values
    areas  = df.iloc[row0:row0 + n_channels, COL_AREA].map(_area_m2).values
    return speeds * areas * 60000.0


def _lane_flows_lpm(df, row0, n_channels):
    return np.abs(_lane_flows_signed(df, row0, n_channels))


def _check_closure(tag_idx, flows1, flows2, pm_lpm):
    """측정 유량 합계가 입구 유량(4 LPM)과 맞는지 검산 (경고만, 결과값 무관).
    1차 통과 유로 합계, 분기 + 2차 통과 유로 합계 모두 4 LPM이 기준. 단면 측정은 원래 작게
    잡히므로(모듈 설명) 0.7~1.3 밖일 때만 측정면 위치·개수 문제로 본다."""
    for tag, total in (("1차 통과 유로", float(np.sum(flows1))),
                       ("분기 + 2차 통과 유로", pm_lpm + float(np.sum(flows2)))):
        ratio = total / TOTAL_FLOW_LPM
        if not (0.7 <= ratio <= 1.3):
            print(f"  ⚠ [{tag_idx}] {tag} 유량 검산 이상: 합계 {total:.3f} LPM "
                  f"(입구 {TOTAL_FLOW_LPM:.1f} LPM의 {ratio*100:.0f}%). 측정면 위치/개수를 확인할 것")


def _check_heat_balance(tag_idx, t_outlet):
    """출구 PAO 온도로 본 흡열이 발열 합계와 맞는지 (경고만). 틀어지면 역류·측정면 문제를 의심."""
    q_out = HEAT_CAPACITY_W_PER_K * (t_outlet - INLET_TEMP_C)
    ratio = q_out / TOTAL_HEAT_W
    if abs(ratio - 1.0) > HEAT_BALANCE_TOL:
        print(f"  ⚠ [{tag_idx}] 열수지 이상: 출구 기준 흡열 {q_out:.1f} W (발열 {TOTAL_HEAT_W:.0f} W의 "
              f"{ratio*100:.0f}%). Opening1 역류 차단, 출구 온도 행을 확인할 것")
    return q_out


def extract_and_save(tag_idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """반환 dict: pressure_drop, temp_std, max_temp, std_pass1, std_pass2,
    power_module_flow(0~1, 정규화), weight(kg), fin_gap_1, fin_gap_2,
    기록 전용: mean_pass1/2, power_module_flow_raw, T_pass1, T_outlet"""
    n1 = bank_values(params, 1)[1] + 1
    n2 = bank_values(params, 2)[1] + 1
    row_lane2, row_pmflow, row_t1, row_out, n_rows = _row_layout(n1, n2)

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
    power_module_flow_raw = pm_lpm / TOTAL_FLOW_LPM
    power_module_flow = pm_lpm / (pm_lpm + float(np.sum(flows2)))   # 정규화 (모듈 설명)
    _check_closure(tag_idx, flows1, flows2, pm_lpm)

    t_pass1 = float(df.iloc[row_t1, COL_MEAN])
    t_outlet = float(df.iloc[row_out, COL_MEAN])
    q_before = HEAT_CAPACITY_W_PER_K * (t_pass1 - INLET_TEMP_C)    # 분기 전 흡열 [W]
    q_out = _check_heat_balance(tag_idx, t_outlet)

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
        "power_module_flow_raw": power_module_flow_raw,
        "T_pass1": t_pass1,
        "T_outlet": t_outlet,
    }
    results.update({f"fin_gap_{b}": bank_gap(params, b) for b in BANKS})

    print(f"[{tag_idx}] 차압:{pressure_drop:.4f}  1차std:{results['std_pass1']:.5f}LPM  "
          f"2차std:{results['std_pass2']:.5f}LPM  온도std:{temp_std:.4f}  최고온도:{max_temp:.2f}  "
          f"분기비:{power_module_flow*100:.1f}% (÷4LPM {power_module_flow_raw*100:.1f}%)  중량:{weight:.3f}kg")
    print(f"      1차 유로 {n1}개 합계={flows1.sum():.4f}  /  2차 유로 {n2}개 합계={flows2.sum():.4f}  "
          f"/  분기 {pm_lpm:.4f} LPM")
    print(f"      1차 통과 후 {t_pass1:.3f}°C (분기 전 흡열 {q_before:.1f} W, 분기 후 {TOTAL_HEAT_W - q_before:.1f} W)  "
          f"출구 {t_outlet:.3f}°C (흡열 {q_out:.1f} W / 발열 {TOTAL_HEAT_W:.0f} W)")
    return results
