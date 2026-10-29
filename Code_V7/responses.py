"""
V7 응답(목적함수·제약) 정의 — 단일 출처

V6 대비 바뀐 것
  · 유로 유량 표준편차(std_pass1/2, CV 재료)를 목적함수에서 뺐다. 유량 균일도는 결국 "채널(슬롯) 안
    온도편차"를 줄이려고 본 간접 지표였는데, 슬롯 하나가 1·2차 통과를 반씩 걸치고 있어 1차·2차 냉각수
    온도 차이는 유량 CV 로 잡히지 않았다. V7 은 발열면(슬롯 바닥 접촉면) 온도로 직접 잰다.
  · 온도 지표 셋은 모두 발열면 17개(슬롯 바닥 13.3 × 183 mm, Total Power 40 W)의 Fields Summary 값에서 나온다.
      max_temp : 17개 발열면 최고온도 중 가장 높은 값                       — 가장 뜨거운 곳
      temp_std : 발열면 평균온도 17개의 표준편차                             — 채널 "간" 균일도 (V6 와 같은 정의)
      temp_in  : 발열면마다 (최고 − 최저)를 구해 17개를 평균                   — 채널 "안" 균일도
    temp_in 은 최고−최저가 기본이다. 캠페인 전 격자 점검(grid_convergence.py)에서 최고−최저가 잡음/신호 기준을
    넘고 면 표준편차는 기준 안이면 표준편차로 바꾼다. 바꾸려면 아래 TEMP_IN_KIND 만 바꾸면 된다(result_parser 가 따라감).
"""
# 채널 안 편차의 슬롯별 정의 — "range"(최고 − 최저) 또는 "sd"(면 온도 표준편차, Fields Summary 의 Stdev 열)
TEMP_IN_KIND = "range"

# 목적함수 — (이름, log 변환 여부). 차압은 스케일이 넓어 log (V5·V6 와 동일)
OBJECTIVES = [
    ("pressure_drop", True),
    ("temp_std", False),
    ("max_temp", False),
    ("temp_in", False),
]
OBJ_NAMES = [o[0] for o in OBJECTIVES]

# 제약조건용 지표 — GPR 학습은 하지만 적응샘플링 방향·종료판정에는 관여하지 않음
#   power_module_flow: 분기 유량 ÷ (분기 + 2차 통과 전체 유량) — 둘 다 핀 없는 통로의 단면 측정면(result_parser.py)
#   psu_margin       : 분기비 − 전원부 필요 분기비 (≥ 0 이면 충족). 필요 분기비 = Q_PSU / (Q_PSU + Q_2차) —
#                      "전원부를 지난 냉각수가 냉각판 출구 온도를 넘지 않는다" (result_parser.py 설명)
CONSTRAINTS = [
    ("power_module_flow", False),
    ("psu_margin",        False),
    ("weight",            False),
]
CONSTRAINT_NAMES = [c[0] for c in CONSTRAINTS]

# 기록 전용 — GPR 학습·적응샘플링·종료판정에는 쓰지 않는다.
#   temp_in_range / temp_in_sd : 채널 안 편차 두 정의 (temp_in 은 이 중 TEMP_IN_KIND 쪽과 같은 값)
#   temp_in_worst : 슬롯별 (최고 − 최저) 중 가장 큰 값 — "평균은 좋은데 한 슬롯만 나쁜" 설계를 확인하는 용도
#   hot_slot / worst_in_slot : 최고온도가 난 슬롯 번호, (최고 − 최저)가 가장 큰 슬롯 번호 (1 ~ 17)
#   power_module_flow_raw    : 분기 유량 ÷ 그 회차 유량 (정규화 전)
#   power_module_flow_energy : 에너지 보존으로 구한 분기비 (T2 − 출구) / (T2 − T1) — 유량 측정과 교차 확인용
#   q_mid_ratio   : 1차 통과 후 통로 단면 유량 ÷ 그 회차 유량 — 단면 유량 측정 편향의 크기 (1 에 가까울수록 정확)
#   psu_ratio_required : 전원부 필요 분기비 / T_psu_coolant : 전원부를 지난 냉각수 온도 (측정 분기비 기준)
#   T_pass1 / T_outlet / T_pass2 : 1차 통과 후 · 출구 · 2차 통과 후(합류 전) PAO 온도
RECORD_ONLY = ["temp_in_range", "temp_in_sd", "temp_in_worst", "hot_slot", "worst_in_slot",
               "power_module_flow_raw", "power_module_flow_energy", "q_mid_ratio",
               "psu_ratio_required", "T_psu_coolant", "T_pass1", "T_outlet", "T_pass2"]

MODELED = OBJECTIVES + CONSTRAINTS
MODELED_NAMES = OBJ_NAMES + CONSTRAINT_NAMES
LOG_RESP = {n: lg for n, lg in MODELED}

UNIT = {
    "pressure_drop": "Pa", "temp_std": "°C", "max_temp": "°C", "temp_in": "°C",
    "power_module_flow": "-", "psu_margin": "-", "weight": "kg",
    "temp_in_range": "°C", "temp_in_sd": "°C", "temp_in_worst": "°C", "hot_slot": "-", "worst_in_slot": "-",
    "power_module_flow_raw": "-", "power_module_flow_energy": "-", "q_mid_ratio": "-",
    "psu_ratio_required": "-", "T_psu_coolant": "°C",
    "T_pass1": "°C", "T_outlet": "°C", "T_pass2": "°C",
}
