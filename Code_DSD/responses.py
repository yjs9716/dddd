"""
V6 응답(목적함수·제약) 정의 — 단일 출처

V5에서는 이 목록이 ML.py 안에 있었고 STD_NAMES 는 result_parser.py 에 있었다.
V6는 DSD_analysis.py 도 같은 목록을 써야 하는데, ML.py/result_parser.py 를 import 하면
AEDT·sklearn 같은 무거운 의존성이 딸려 오므로 목록만 여기로 뺐다.
"""
# 통과별 유로 유량 표준편차 [LPM]
STD_NAMES = ["std_pass1", "std_pass2"]

# 목적함수 — (이름, log 변환 여부). 차압은 스케일이 넓어 log (V5와 동일)
OBJECTIVES = (
    [("pressure_drop", True)]
    + [("temp_std", False), ("max_temp", False)]
    + [(n, False) for n in STD_NAMES]
)
OBJ_NAMES = [o[0] for o in OBJECTIVES]

# 제약조건용 지표 — GPR 학습은 하지만 적응샘플링 방향·종료판정에는 관여하지 않음
CONSTRAINTS = [
    ("power_module_flow", False),
    ("weight",            False),
]
CONSTRAINT_NAMES = [c[0] for c in CONSTRAINTS]

# 기록 전용 — GPR 학습·적응샘플링·종료판정에는 쓰지 않는다.
#   패스별 유로 유량의 실측 평균 [LPM]. 균일도를 변동계수 CV = std_pass / mean_pass 로
#   계산하기 위한 재료(최적화 단계에서 사후 계산). 유로 합계 = mean × 유로 수 → 질량 보존 확인용.
RECORD_ONLY = ["mean_pass1", "mean_pass2"]

MODELED = OBJECTIVES + CONSTRAINTS
MODELED_NAMES = OBJ_NAMES + CONSTRAINT_NAMES
LOG_RESP = {n: lg for n, lg in MODELED}

UNIT = {
    "pressure_drop": "Pa", "temp_std": "°C", "max_temp": "°C",
    "std_pass1": "LPM", "std_pass2": "LPM", "power_module_flow": "-", "weight": "kg",
    "mean_pass1": "LPM", "mean_pass2": "LPM",
}
