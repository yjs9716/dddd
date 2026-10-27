"""
V7 — Icepak 결과 CSV 파싱 (V6 result_parser.py 기반)

V6 대비 변경점
  · 행 구조가 설계와 무관하게 고정이다 (icepak.py run_icepak 주석과 1:1, S = N_SOURCE = 17):
      행 0 ~ S−1 : source01~ 발열면(슬롯 바닥 접촉면) 온도 — 최저·최고·평균·표준편차
      행 S       : Fan1_Passage 차압
      행 S+1     : Rectangle1 유량 (전원모듈 분기 입구)
      행 S+2     : Q_pass2 유량 (2차 통과 출구 통로 = 2차 통과 전체)
      행 S+3     : Q_mid 유량 (1차 통과 후 가운데 통로, 4 LPM 이어야 함)
      행 S+4     : T_pass1 온도 / 행 S+5 : Opening1 온도 (출구) / 행 S+6 : T_pass2 온도
  · 온도 지표 셋 (정의는 responses.py):
      max_temp = maxᵢ 최고ᵢ,   temp_std = std(평균ᵢ),   temp_in = meanᵢ(최고ᵢ − 최저ᵢ)  [TEMP_IN_KIND="sd" 면 표준편차ᵢ]
  · 열 위치를 CSV 머리줄의 이름(Min / Max / Mean / Stdev / Area)으로 찾는다. 머리줄을 못 찾으면 V6 위치
    (7 / 8 / 9 / 10 / 11)를 쓰고, 어느 쪽이든 발열면 행에서 최저 ≤ 평균 ≤ 최고 인지 검사해 어긋나면 멈춘다.
  · 분기비 power_module_flow = 분기 ÷ (분기 + 2차 통과 전체). 두 유량 모두 핀 없는 통로 단면에서 같은 방식으로
    잰 값이라 단면 측정의 공통 편향(벽 쪽 셀에서 속도가 0으로 보간돼 유량이 작게 잡힘 — V6 에서 1차 통과 합계
    3.3 LPM)이 비에서 상쇄된다. 교차 확인용으로 둘을 더 기록한다:
      q_mid_ratio              = Q_mid ÷ 4 LPM — 그 편향의 크기 (1 에 가까울수록 정확)
      power_module_flow_energy = (T2 − T출구) ÷ (T2 − T1) — 에너지 보존 분기비. 해석에 PSU 열이 없어 분기 쪽
                                 냉각수는 T1 그대로 출구에서 2차 통과 냉각수(T2)와 섞인다.
  · 열수지(출구 흡열 ÷ 발열 합계)가 HEAT_BALANCE_FAIL 넘게 어긋나면 이 회차를 실패로 처리한다 — 역류·측정면
    오류가 의심되는 결과를 학습 데이터에 넣지 않으려고. HEAT_BALANCE_WARN 넘으면 경고만 한다.

그대로 (V6): 중량 = 알루미늄(SolidWorks) + PAO(전체 부피 − 알루미늄 부피), 1·2차 통과 후·출구 PAO 온도 기록.
"""
import re

import numpy as np
import pandas as pd

from fins import BANKS, bank_gap
from icepak import PAO_DENSITY, PAO_SPECIFIC_HEAT, INLET_TEMP_C, SOURCE_POWER_W, N_SOURCE
from responses import TEMP_IN_KIND

# ⚠ 판재 외형이 V5와 같다는 전제의 값 — 형상을 바꿨다면 SolidWorks에서 다시 실측할 것
FULL_SOLID_VOLUME_MM3 = 2341073.1

ROW_SOURCE = 0
ROW_DP     = ROW_SOURCE + N_SOURCE
ROW_PM     = ROW_DP + 1      # Rectangle1 (분기)
ROW_Q2     = ROW_DP + 2      # Q_pass2
ROW_QMID   = ROW_DP + 3      # Q_mid
ROW_T1     = ROW_DP + 4
ROW_OUT    = ROW_DP + 5
ROW_T2     = ROW_DP + 6
N_ROWS     = ROW_T2 + 1

SKIP_ROWS = 5                # 머리말 줄 수 (V6 와 같음)
COL_NAME = 2
DEFAULT_COLS = {"min": 7, "max": 8, "mean": 9, "sd": 10, "area": 11}   # 머리줄을 못 찾을 때 (V6 위치)
_HEADER_KEYS = {"min": ("min",), "max": ("max",), "mean": ("mean", "avg", "average"),
                "sd": ("stdev", "std", "standard"), "area": ("area", "volume")}

TOTAL_FLOW_LPM = 4.0
# 4 LPM 전체를 1 °C 올리는 데 드는 열 [W/K] (≈117.5)
HEAT_CAPACITY_W_PER_K = PAO_DENSITY * PAO_SPECIFIC_HEAT * TOTAL_FLOW_LPM / 60000.0
TOTAL_HEAT_W = N_SOURCE * SOURCE_POWER_W     # 17 × 40 = 680 W
HEAT_BALANCE_WARN = 0.05                     # 출구 열수지 경고 기준
HEAT_BALANCE_FAIL = 0.10                     # 이보다 어긋나면 실패 처리 (V6 정상 회차는 3% 안팎)
FLOW_RATIO_WARN = (0.7, 1.3)                 # Q_mid / 4, (분기 + 2차) / 4 — 벗어나면 경고
FLOW_RATIO_FAIL = (0.5, 1.5)                 # 벗어나면 측정면 위치가 틀린 것으로 보고 실패 처리


def _num(cell):
    """CSV 칸 → float. AEDT 가 계산하지 못한 값('-nan(ind)' 등)은 nan."""
    try:
        return float(str(cell).strip().split()[0])
    except (ValueError, IndexError):
        return np.nan


def _columns(path):
    """머리줄에서 Min/Max/Mean/Stdev/Area 열 위치를 찾는다. 못 찾으면 V6 위치. 반환: ({이름: 열}, 출처)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        head = [next(f, "") for _ in range(SKIP_ROWS + 2)]
    for line in head:
        for sep in (",", "\t", ";"):
            cells = [c.strip().strip('"').lower() for c in line.split(sep)]
            found = {}
            for key, words in _HEADER_KEYS.items():
                hit = [i for i, c in enumerate(cells) if any(re.match(rf"{w}\b", c) for w in words)]
                if hit:
                    found[key] = hit[0]
            if {"min", "max", "mean", "area"} <= set(found):
                return found, "머리줄"
    return dict(DEFAULT_COLS), "기본 위치(V6)"


def _row_value(df, row, col, tag_idx, what):
    """목적함수·제약에 쓰는 값 하나. 계산되지 않았으면(nan) 행 이름을 밝히고 실패 처리."""
    v = _num(df.iloc[row, col])
    if not np.isfinite(v):
        raise ValueError(f"[{tag_idx}] {what} 값이 계산되지 않음(nan): 행 {row} {df.iloc[row, COL_NAME]}")
    return v


def _record_value(df, row, col, tag_idx, what):
    """기록 전용 값 하나. 계산되지 않았으면 nan 으로 남기고 경고만 한다(해석 결과는 살림)."""
    v = _num(df.iloc[row, col])
    if not np.isfinite(v):
        print(f"  ⚠ [{tag_idx}] {what} 값이 계산되지 않음(nan) — 빈칸으로 기록: {df.iloc[row, COL_NAME]}")
    return v


def _flow_lpm(df, row, cols, tag_idx, what):
    """측정면 유량 [LPM] = |평균 법선 속도| × 면적 (벽 속 고체 부분은 속도 0 이라 유량에 영향 없음)."""
    speed = _row_value(df, row, cols["mean"], tag_idx, f"{what} 평균 유속")
    area = _row_value(df, row, cols["area"], tag_idx, f"{what} 측정면 넓이")
    return abs(speed) * area * 60000.0


def _check_ratio(tag_idx, what, ratio):
    if not FLOW_RATIO_FAIL[0] <= ratio <= FLOW_RATIO_FAIL[1]:
        raise ValueError(f"[{tag_idx}] {what} = 입구 유량의 {ratio*100:.0f}% — 측정면 위치가 통로 단면에서 벗어난 것으로 보임")
    if not FLOW_RATIO_WARN[0] <= ratio <= FLOW_RATIO_WARN[1]:
        print(f"  ⚠ [{tag_idx}] {what} = 입구 유량의 {ratio*100:.0f}% — 단면 유량 측정 편향이 큼. 측정면·메시를 확인할 것")


def _check_heat_balance(tag_idx, t_outlet):
    """출구 PAO 온도로 본 흡열 ÷ 발열 합계. 크게 어긋나면 실패, 조금 어긋나면 경고. 반환: (흡열 W, 비)."""
    q_out = HEAT_CAPACITY_W_PER_K * (t_outlet - INLET_TEMP_C)
    ratio = q_out / TOTAL_HEAT_W
    msg = (f"열수지: 출구 기준 흡열 {q_out:.1f} W (발열 {TOTAL_HEAT_W:.0f} W의 {ratio*100:.1f}%). "
           "Opening1 역류 차단, 출구 온도 행, 발열면 Source 경계를 확인할 것")
    if not np.isfinite(ratio) or abs(ratio - 1.0) > HEAT_BALANCE_FAIL:
        raise ValueError(f"[{tag_idx}] {msg}")
    if abs(ratio - 1.0) > HEAT_BALANCE_WARN:
        print(f"  ⚠ [{tag_idx}] {msg}")
    return q_out, ratio


def extract_and_save(tag_idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3):
    """반환 dict — 목적함수: pressure_drop, temp_std, max_temp, temp_in / 제약: power_module_flow, weight /
    기록 전용(responses.RECORD_ONLY): temp_in_range, temp_in_sd, temp_in_worst, hot_slot, worst_in_slot,
    power_module_flow_raw, power_module_flow_energy, q_mid_ratio, T_pass1, T_outlet, T_pass2 / fin_gap_1, fin_gap_2"""
    cols, col_src = _columns(result_path)
    df = pd.read_csv(result_path, header=None, skiprows=SKIP_ROWS, sep=None, engine="python",
                     on_bad_lines="skip")
    if len(df) < N_ROWS:
        raise ValueError(f"CSV 행이 {len(df)}개뿐 — {N_ROWS}개 기대 (발열면 {N_SOURCE} + 7).\n"
                         "  icepak.py 의 Calculation 순서와 result_parser.py 의 ROW_* 가 같은지 확인할 것")
    names = [str(df.iloc[r, COL_NAME]) for r in range(N_ROWS)]
    bad = [n for n in names[:N_SOURCE] if "source" not in n.lower()]
    if bad:
        raise ValueError(f"[{tag_idx}] 발열면 행 이름이 source 가 아님: {bad[:3]} — 행 순서가 어긋남")

    # ── 발열면 온도 ──
    src = range(ROW_SOURCE, ROW_SOURCE + N_SOURCE)
    s_min = np.array([_row_value(df, r, cols["min"], tag_idx, "발열면 최저온도") for r in src])
    s_max = np.array([_row_value(df, r, cols["max"], tag_idx, "발열면 최고온도") for r in src])
    s_mean = np.array([_row_value(df, r, cols["mean"], tag_idx, "발열면 평균온도") for r in src])
    if np.any(s_min > s_mean + 1e-6) or np.any(s_mean > s_max + 1e-6):
        raise ValueError(f"[{tag_idx}] 발열면 행에서 최저 ≤ 평균 ≤ 최고가 아님 — 열 위치({col_src} {cols})가 틀림. "
                         "CSV 머리줄을 확인해 result_parser.DEFAULT_COLS 를 고칠 것")
    if "sd" in cols:
        s_sd = np.array([_num(df.iloc[r, cols["sd"]]) for r in src])
    else:
        s_sd = np.full(N_SOURCE, np.nan)
    s_range = s_max - s_min

    max_temp = float(s_max.max())
    temp_std = float(np.std(s_mean))
    temp_in_range = float(s_range.mean())
    temp_in_sd = float(s_sd.mean()) if np.all(np.isfinite(s_sd)) else np.nan
    if TEMP_IN_KIND == "range":
        temp_in = temp_in_range
    elif TEMP_IN_KIND == "sd":
        if not np.isfinite(temp_in_sd):
            raise ValueError(f"[{tag_idx}] responses.TEMP_IN_KIND='sd' 인데 표준편차 열이 없거나 nan ({col_src} {cols})")
        temp_in = temp_in_sd
    else:
        raise ValueError(f"responses.TEMP_IN_KIND 는 'range' 또는 'sd': {TEMP_IN_KIND}")

    # ── 차압·유량 ──
    pressure_drop = _row_value(df, ROW_DP, cols["mean"], tag_idx, "차압")
    pm_lpm = _flow_lpm(df, ROW_PM, cols, tag_idx, "분기(Rectangle1)")
    q2_lpm = _flow_lpm(df, ROW_Q2, cols, tag_idx, "2차 통과(Q_pass2)")
    qmid_lpm = _flow_lpm(df, ROW_QMID, cols, tag_idx, "1차 통과 후(Q_mid)")
    power_module_flow = pm_lpm / (pm_lpm + q2_lpm)
    power_module_flow_raw = pm_lpm / TOTAL_FLOW_LPM
    q_mid_ratio = qmid_lpm / TOTAL_FLOW_LPM
    _check_ratio(tag_idx, "1차 통과 후 통로 유량(Q_mid)", q_mid_ratio)
    _check_ratio(tag_idx, "분기 + 2차 통과 유량", (pm_lpm + q2_lpm) / TOTAL_FLOW_LPM)

    # ── PAO 온도·열수지 ──
    t_pass1 = _record_value(df, ROW_T1, cols["mean"], tag_idx, "1차 통과 후 온도")
    t_outlet = _row_value(df, ROW_OUT, cols["mean"], tag_idx, "출구 온도")
    t_pass2 = _record_value(df, ROW_T2, cols["mean"], tag_idx, "2차 통과 후 온도")
    q_out, hb = _check_heat_balance(tag_idx, t_outlet)
    q_before = HEAT_CAPACITY_W_PER_K * (t_pass1 - INLET_TEMP_C)    # 분기 전 흡열 [W]
    dt21 = t_pass2 - t_pass1
    pm_energy = (t_pass2 - t_outlet) / dt21 if np.isfinite(dt21) and abs(dt21) > 0.05 else np.nan

    pao_volume_mm3 = FULL_SOLID_VOLUME_MM3 - float(aluminum_volume_mm3)
    if pao_volume_mm3 <= 0:
        raise ValueError(f"PAO 부피가 0 이하({pao_volume_mm3:.1f} mm^3) — FULL_SOLID_VOLUME_MM3 확인")
    weight = float(aluminum_mass_kg) + pao_volume_mm3 * 1e-9 * PAO_DENSITY

    results = {
        "pressure_drop": pressure_drop,
        "temp_std": temp_std,
        "max_temp": max_temp,
        "temp_in": temp_in,
        "power_module_flow": power_module_flow,
        "weight": weight,
        # 기록 전용 (responses.RECORD_ONLY)
        "temp_in_range": temp_in_range,
        "temp_in_sd": temp_in_sd,
        "temp_in_worst": float(s_range.max()),
        "hot_slot": int(np.argmax(s_max)) + 1,
        "worst_in_slot": int(np.argmax(s_range)) + 1,
        "power_module_flow_raw": power_module_flow_raw,
        "power_module_flow_energy": pm_energy,
        "q_mid_ratio": q_mid_ratio,
        "T_pass1": t_pass1,
        "T_outlet": t_outlet,
        "T_pass2": t_pass2,
    }
    results.update({f"fin_gap_{b}": bank_gap(params, b) for b in BANKS})

    print(f"[{tag_idx}] 최고온도:{max_temp:.2f}  채널간 편차:{temp_std:.4f}  채널안 편차:{temp_in:.4f} ({TEMP_IN_KIND}, "
          f"최악 {results['temp_in_worst']:.3f} @슬롯{results['worst_in_slot']})  차압:{pressure_drop:.1f}  "
          f"분기비:{power_module_flow*100:.1f}% (에너지 {pm_energy*100:.1f}%, ÷4LPM {power_module_flow_raw*100:.1f}%)  "
          f"중량:{weight:.3f}kg")
    print(f"      발열면 {N_SOURCE}개 최저 {s_min.min():.2f} ~ 최고 {max_temp:.2f} °C (가장 뜨거운 슬롯 {results['hot_slot']}) · "
          f"열 위치 {col_src}")
    print(f"      유량: 분기 {pm_lpm:.4f} + 2차 {q2_lpm:.4f} LPM · 1차 통과 후 {qmid_lpm:.4f} LPM "
          f"(입구 {TOTAL_FLOW_LPM:.1f} LPM의 {q_mid_ratio*100:.0f}%)")
    print(f"      PAO 온도: 1차 후 {t_pass1:.3f} (분기 전 흡열 {q_before:.1f} W) · 2차 후 {t_pass2:.3f} · "
          f"출구 {t_outlet:.3f} °C (흡열 {q_out:.1f} W / 발열 {TOTAL_HEAT_W:.0f} W = {hb*100:.1f}%)")
    return results
