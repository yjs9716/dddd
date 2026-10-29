"""
V7 — Icepak 결과 CSV 파싱 (V6 result_parser.py 기반)

V6 대비 변경점
  · 행 구조가 설계와 무관하게 고정이다 (icepak.py run_icepak 주석과 1:1, S = N_SOURCE = 17):
      행 0 ~ S−1 : source01~ 발열면(슬롯 바닥 접촉면) 온도 — 최저·최고·평균·표준편차
      행 S       : Fan1_Passage 차압
      행 S+1     : Rectangle1 유량 (전원모듈 분기 입구)
      행 S+2     : Q_pass2 유량 (2차 통과 출구 통로 = 2차 통과 전체)
      행 S+3     : Q_mid 유량 (1차 통과 후 가운데 통로, 입구 유량과 같아야 함)
      행 S+4     : T_pass1 온도 / 행 S+5 : Opening1 온도 (출구) / 행 S+6 : T_pass2 온도
  · 온도 지표 셋 (정의는 responses.py):
      max_temp = maxᵢ 최고ᵢ,   temp_std = std(평균ᵢ),   temp_in = meanᵢ(최고ᵢ − 최저ᵢ)  [TEMP_IN_KIND="sd" 면 표준편차ᵢ]
  · 열 위치를 CSV 머리줄의 이름(Min / Max / Mean / Stdev / Area)으로 찾는다. 머리줄을 못 찾으면 V6 위치
    (7 / 8 / 9 / 10 / 11)를 쓰고, 어느 쪽이든 발열면 행에서 최저 ≤ 평균 ≤ 최고 인지 검사해 어긋나면 멈춘다.
  · 분기비 power_module_flow = 분기 ÷ (분기 + 2차 통과 전체). 두 유량 모두 핀 없는 통로 단면에서 같은 방식으로
    잰 값이라 단면 측정의 공통 편향(벽 쪽 셀에서 속도가 0으로 보간돼 유량이 작게 잡힘 — V6 에서 1차 통과 합계
    3.3 LPM)이 비에서 상쇄된다. 교차 확인용으로 둘을 더 기록한다:
      q_mid_ratio              = Q_mid ÷ 그 회차 유량 — 그 편향의 크기 (1 에 가까울수록 정확)
      power_module_flow_energy = (T2 − T출구) ÷ (T2 − T1) — 에너지 보존 분기비. 해석에 PSU 열이 없어 분기 쪽
                                 냉각수는 T1 그대로 출구에서 2차 통과 냉각수(T2)와 섞인다.
  · 열수지(출구 흡열 ÷ 발열 합계)가 HEAT_BALANCE_FAIL 넘게 어긋나면 이 회차를 실패로 처리한다 — 역류·측정면
    오류가 의심되는 결과를 학습 데이터에 넣지 않으려고. HEAT_BALANCE_WARN 넘으면 경고만 한다.
  · 냉각수 유량이 후보 변수라(params["flow_lpm"]) 흡열 계산·유량 비율은 그 회차 유량으로 한다(heat_capacity_w_per_k).
  · 전원부(PSU) 분기 조건 — 제약 psu_margin = 분기비 − 필요 분기비 (≥ 0 이면 충족)
      전원부 실장 형태·허용 온도는 정해지지 않고 총 손실(PSU_LOSS_W)만 주어지므로, 실장 형태와 무관한 냉각수 에너지
      기준을 쓴다: "전원부를 지난 냉각수 온도가 냉각판 출구 온도를 넘지 않는다" (= CCA 2차 통과 냉각수보다 뜨겁지 않다).
      1차 통과 후 냉각수(T1)가 같은 온도로 2차 통과와 분기로 나뉜다고 보면(분기 통로는 CCA 발열 영역 밖)
          필요 분기비 = Q_PSU / (Q_PSU + Q_2차),   Q_2차 = 발열 합계 − 분기 전 흡열(유량 × c_p × (T1 − 입구))
  · 중량 = 알루미늄 질량 + PAO 부피 × 밀도,  PAO 부피 = 꽉 채운 판 부피(깊이 L) − 알루미늄 부피 (둘 다 SolidWorks)
      V6 는 꽉 채운 부피를 상수로 썼지만 V7 은 유로 깊이가 변수라 꽉 채운 부피도 깊이를 따라 바뀐다.
      SolidWorks 모델은 판 바닥 기준으로 첫 보스 두께(= 깊이 + 2.5)만 바뀌므로 꽉 채운 부피는 깊이에 정확히 비례한다:
          꽉 채운 부피(L) = V₈ + (L − 8) × (V₁₂ − V₈) / 4      (full_solid_volume_mm3)
      V₈ · V₁₂ 는 유로 빼기 피처를 억제하고 잰 어셈블리 부피(아래 상수). Icepak 냉각수 덩어리 부피로 낸 중량
      (weight_icepak)을 같이 기록해 두 방식의 차이가 설계마다 일정한지 검산한다.

그대로 (V6): 1·2차 통과 후·출구 PAO 온도 기록.
"""
import re

import numpy as np
import pandas as pd

from fins import BANKS, bank_gap
from fins import NOMINAL_DEPTH_MM
from icepak import PAO_DENSITY, PAO_SPECIFIC_HEAT, INLET_TEMP_C, SOURCE_POWER_W, N_SOURCE, NOMINAL_FLOW_LPM
from responses import TEMP_IN_KIND

# 꽉 채운 판(plate + plate_base, 유로 빼기 피처 억제) 부피 [mm³] — V7 SolidWorks 모델에서 잰 값 (모듈 설명)
#   V4~V6 상수 2,341,073.1 은 V4 형상 기준일 수 있어 V7 에서 다시 쟀다(55,719 mm³ 작음 → V6 중량은 약 44 g 무겁게 계산됨).
#   SolidWorks 모델을 바꾸면 두 값을 같은 방법으로 다시 잴 것.
FULL_SOLID_VOLUME_AT_8_MM3  = 2285354.2      # fin_height = 8
FULL_SOLID_VOLUME_AT_12_MM3 = 2918447.8      # fin_height = 12
FULL_SOLID_PER_MM_DEPTH = (FULL_SOLID_VOLUME_AT_12_MM3 - FULL_SOLID_VOLUME_AT_8_MM3) / 4.0   # ≈ 158,273 mm³/mm
#   검산: fin_height = 10 에서 잰 값 2,601,901 = 식의 값 2,601,901.0 — 깊이에 정확히 비례함을 확인


def full_solid_volume_mm3(depth):
    """유로 깊이 depth [mm] 일 때 꽉 채운 판 부피 [mm³] — 깊이에 비례 (모듈 설명)."""
    return FULL_SOLID_VOLUME_AT_8_MM3 + (float(depth) - NOMINAL_DEPTH_MM) * FULL_SOLID_PER_MM_DEPTH

# 전원부(PSU) 총 손실 [W] — 800 W급, 효율 90% 가정: CCA 680 W × (1/0.9 − 1). 사양이 확정되면 이 값만 바꾼다.
PSU_LOSS_W = 75.6

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

TOTAL_HEAT_W = N_SOURCE * SOURCE_POWER_W     # 17 × 40 = 680 W
HEAT_BALANCE_WARN = 0.05                     # 출구 열수지 경고 기준
HEAT_BALANCE_FAIL = 0.10                     # 이보다 어긋나면 실패 처리 (V6 정상 회차는 3% 안팎)
FLOW_RATIO_WARN = (0.7, 1.3)                 # Q_mid ÷ 유량, (분기 + 2차) ÷ 유량 — 벗어나면 경고
FLOW_RATIO_FAIL = (0.5, 1.5)                 # 벗어나면 측정면 위치가 틀린 것으로 보고 실패 처리


def heat_capacity_w_per_k(flow_lpm=NOMINAL_FLOW_LPM):
    """냉각수 전체를 1 °C 올리는 데 드는 열 [W/K] = 밀도 × 비열 × 유량 (4 LPM 에서 ≈117.5)."""
    return PAO_DENSITY * PAO_SPECIFIC_HEAT * float(flow_lpm) / 60000.0


def psu_required_ratio(t_pass1, flow_lpm, q_psu=PSU_LOSS_W):
    """전원부 필요 분기비 = Q_PSU / (Q_PSU + Q_2차) (모듈 설명). 반환: (필요 분기비, Q_2차 W)."""
    q_2nd = TOTAL_HEAT_W - heat_capacity_w_per_k(flow_lpm) * (t_pass1 - INLET_TEMP_C)
    return q_psu / (q_psu + max(q_2nd, 1e-6)), q_2nd


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


def _check_heat_balance(tag_idx, t_outlet, flow_lpm):
    """출구 PAO 온도로 본 흡열 ÷ 발열 합계. 크게 어긋나면 실패, 조금 어긋나면 경고. 반환: (흡열 W, 비)."""
    q_out = heat_capacity_w_per_k(flow_lpm) * (t_outlet - INLET_TEMP_C)
    ratio = q_out / TOTAL_HEAT_W
    msg = (f"열수지: 출구 기준 흡열 {q_out:.1f} W (발열 {TOTAL_HEAT_W:.0f} W의 {ratio*100:.1f}%). "
           "Opening1 역류 차단, 출구 온도 행, 발열면 Source 경계를 확인할 것")
    if not np.isfinite(ratio) or abs(ratio - 1.0) > HEAT_BALANCE_FAIL:
        raise ValueError(f"[{tag_idx}] {msg}")
    if abs(ratio - 1.0) > HEAT_BALANCE_WARN:
        print(f"  ⚠ [{tag_idx}] {msg}")
    return q_out, ratio


def extract_and_save(tag_idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3, pao_volume_mm3=None):
    """반환 dict — 목적함수: pressure_drop, temp_std, max_temp, temp_in / 제약: power_module_flow, psu_margin, weight /
    기록 전용(responses.RECORD_ONLY): temp_in_range, temp_in_sd, temp_in_worst, hot_slot, worst_in_slot,
    power_module_flow_raw, power_module_flow_energy, q_mid_ratio, psu_ratio_required, T_psu_coolant,
    T_pass1, T_outlet, T_pass2, weight_icepak / fin_gap_1, fin_gap_2
    pao_volume_mm3 : Icepak 냉각수 덩어리(PAO_Separate1) 부피 — run_icepak 의 세 번째 반환값 (검산용 weight_icepak)."""
    flow = float(params.get("flow_lpm", NOMINAL_FLOW_LPM))
    cap = heat_capacity_w_per_k(flow)
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
    power_module_flow_raw = pm_lpm / flow
    q_mid_ratio = qmid_lpm / flow
    _check_ratio(tag_idx, "1차 통과 후 통로 유량(Q_mid)", q_mid_ratio)
    _check_ratio(tag_idx, "분기 + 2차 통과 유량", (pm_lpm + q2_lpm) / flow)

    # ── PAO 온도·열수지 ──
    t_pass1 = _row_value(df, ROW_T1, cols["mean"], tag_idx, "1차 통과 후 온도")      # 전원부 조건에 쓰여 필수
    t_outlet = _row_value(df, ROW_OUT, cols["mean"], tag_idx, "출구 온도")
    t_pass2 = _record_value(df, ROW_T2, cols["mean"], tag_idx, "2차 통과 후 온도")
    q_out, hb = _check_heat_balance(tag_idx, t_outlet, flow)
    q_before = cap * (t_pass1 - INLET_TEMP_C)    # 분기 전 흡열 [W]
    dt21 = t_pass2 - t_pass1
    pm_energy = (t_pass2 - t_outlet) / dt21 if np.isfinite(dt21) and abs(dt21) > 0.05 else np.nan

    # ── 전원부 분기 조건 (모듈 설명) ──
    r_req, q_2nd = psu_required_ratio(t_pass1, flow)
    psu_margin = power_module_flow - r_req
    t_psu = t_pass1 + PSU_LOSS_W / (cap * power_module_flow)          # 전원부를 지난 냉각수 온도 (측정 분기비 기준)
    t_out_psu = INLET_TEMP_C + (TOTAL_HEAT_W + PSU_LOSS_W) / cap      # 전원부 열까지 넣은 냉각판 출구 온도

    # ── 중량 (모듈 설명) ──
    depth = float(params.get("fin_height", NOMINAL_DEPTH_MM))
    full_mm3 = full_solid_volume_mm3(depth)
    pao_mm3 = full_mm3 - float(aluminum_volume_mm3)
    if pao_mm3 <= 0:
        raise ValueError(f"[{tag_idx}] PAO 부피가 0 이하({pao_mm3:.1f} mm³) — 꽉 채운 부피 {full_mm3:.1f} < 알루미늄 부피. "
                         "result_parser.FULL_SOLID_VOLUME_AT_* 가 지금 SolidWorks 모델과 맞는지 확인할 것")
    weight = float(aluminum_mass_kg) + pao_mm3 * 1e-9 * PAO_DENSITY
    pao_icepak = float(pao_volume_mm3) if pao_volume_mm3 is not None else np.nan
    weight_icepak = float(aluminum_mass_kg) + pao_icepak * 1e-9 * PAO_DENSITY

    results = {
        "pressure_drop": pressure_drop,
        "temp_std": temp_std,
        "max_temp": max_temp,
        "temp_in": temp_in,
        "power_module_flow": power_module_flow,
        "psu_margin": psu_margin,
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
        "psu_ratio_required": r_req,
        "T_psu_coolant": t_psu,
        "T_pass1": t_pass1,
        "T_outlet": t_outlet,
        "T_pass2": t_pass2,
        "weight_icepak": weight_icepak,
    }
    results.update({f"fin_gap_{b}": bank_gap(params, b) for b in BANKS})

    print(f"[{tag_idx}] 최고온도:{max_temp:.2f}  채널간 편차:{temp_std:.4f}  채널안 편차:{temp_in:.4f} ({TEMP_IN_KIND}, "
          f"최악 {results['temp_in_worst']:.3f} @슬롯{results['worst_in_slot']})  차압:{pressure_drop:.1f}  "
          f"분기비:{power_module_flow*100:.1f}% (필요 {r_req*100:.1f}%, 에너지 {pm_energy*100:.1f}%, "
          f"÷유량 {power_module_flow_raw*100:.1f}%)  중량:{weight:.3f}kg  [{flow:g} LPM · 깊이 {depth:g} mm]")
    print(f"      발열면 {N_SOURCE}개 최저 {s_min.min():.2f} ~ 최고 {max_temp:.2f} °C (가장 뜨거운 슬롯 {results['hot_slot']}) · "
          f"열 위치 {col_src}")
    print(f"      유량: 분기 {pm_lpm:.4f} + 2차 {q2_lpm:.4f} LPM · 1차 통과 후 {qmid_lpm:.4f} LPM "
          f"(입구 {flow:g} LPM의 {q_mid_ratio*100:.0f}%)")
    print(f"      PAO 온도: 1차 후 {t_pass1:.3f} (분기 전 흡열 {q_before:.1f} W) · 2차 후 {t_pass2:.3f} · "
          f"출구 {t_outlet:.3f} °C (흡열 {q_out:.1f} W / 발열 {TOTAL_HEAT_W:.0f} W = {hb*100:.1f}%)")
    print(f"      전원부({PSU_LOSS_W:g} W): 분기비 {power_module_flow*100:.1f}% / 필요 {r_req*100:.1f}% (여유 {psu_margin*100:+.1f}%p, "
          f"Q_2차 {q_2nd:.1f} W) · 전원부 지난 냉각수 {t_psu:.2f} °C / 판 출구(전원부 열 포함) {t_out_psu:.2f} °C")
    print(f"      중량: {weight:.4f} kg (PAO {pao_mm3:.0f} mm³ = 꽉 채운 부피 {full_mm3:.0f} − 알루미늄 {float(aluminum_volume_mm3):.0f})"
          + (f" · 검산: Icepak 냉각수 부피 {pao_icepak:.0f} mm³ → {weight_icepak:.4f} kg "
             f"(차이 {(weight_icepak - weight) * 1000:+.1f} g)" if np.isfinite(pao_icepak) else ""))
    return results
