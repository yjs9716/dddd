"""
V7 경로 설정 — DSD 선별(후보 13개) → OLHD + GPR 적응샘플링

V6 대비 바뀐 것
  · 발열: FR-4 블록(부피 발열) → 슬롯 바닥 접촉면 2D 면 발열(Total Power 40 W). 지표가 온도 기준으로 바뀌어
    V6 결과(results_v6.csv)와 섞이면 안 되므로 작업폴더 자체를 따로 둔다.
  · 후보 변수에 냉각수 유량(flow_lpm)과 유로 깊이(fin_height)를 더해 13개가 됐다. 그래서 선별(DSD)도 V7 조건으로
    다시 하고, OLHD 실험점도 새로 만든다 — V6 의 screening_decision.json · olhd_plan.csv 는 쓰지 않는다.

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\V7   (V7 작업폴더, 전부 여기)
    ├─ AEDT           : V7 AEDT 프로젝트 저장 위치 (없으면 만든다)
    ├─ Code           : 이 코드(Code_V7 폴더 내용물)를 옮겨 넣는 위치
    ├─ Result
    │   ├─ DSD        : 1단계 선별 — dsd_plan.csv, result_dsd_000.csv... (Icepak 원본),
    │   │               results_dsd.csv / failed_dsd.csv (ML.py 관리),
    │   │               dsd_effects.csv / screening_decision.json (DSD_analysis.py 생성)
    │   ├─ OLHD       : 2단계 대리모델 — olhd_plan.csv / olhd_plan_meta.json (처음 한 번 생성),
    │   │               result_000.csv... (Icepak 원본), results_v7.csv / failed_v7.csv (ML.py 관리)
    │   ├─ GCI        : 캠페인 전 격자 점검 (grid_convergence.py)
    │   ├─ PASS       : 1·2·4패스 비교 (pass_compare.py)
    │   └─ VERIFY     : 검증 해석 (verify_point.py)
    └─ Solidworks     : plate_base.SLDPRT, flowpath.SLDASM ← V6 Solidworks 에서 복사한 뒤 fin_height 를 추가
        └─ Step

⚠ 시작 전 준비
  1) SolidWorks 두 파일을 복사해 둘 것.
  2) SolidWorks Equation Manager 에 형상 변수 12개가 전부 전역변수로 있어야 한다
     (선별로 고정된 변수도 매 회차 파이썬이 고정값을 써넣는다. 유량 flow_lpm 은 SolidWorks 에 쓰지 않는다):
       input_thick, input_angle, power_input_thick, mid_thick, mid_angle,
       mid_input_thick, output_thick,
       fin_thick_1, fin_count_1, fin_thick_2, fin_count_2,
       fin_height                         ← V7 추가 (유로 깊이 = 핀 높이)
     수식:
       "fin_gap_1" = (86.5 - "fin_count_1" * "fin_thick_1") / ("fin_count_1" + 1)
       "fin_gap_2" = (86.5 - "fin_count_2" * "fin_thick_2") / ("fin_count_2" + 1)
       첫 보스 두께 = "fin_height" + 2.5,  유로 빼기 깊이(통로·홈 전부) = "fin_height"
       (판 바닥이 기준 — 바닥·덮개 2.5 mm·포트 높이는 그대로, 유로 천장 위가 깊이만큼 올라간다. WORKFLOW.md)

테스트용: 환경변수 V7_CAMPAIGN_DIR 을 주면 BASE_V7 대신 그 폴더를 쓴다 (실제 캠페인에서는 설정하지 말 것).
"""
import os

BASE_V7 = os.environ.get("V7_CAMPAIGN_DIR",
                         r"E:\Thermal_Anlaysis\Liquid_plate\V7")   # V7 작업폴더

AEDT_DIR       = os.path.join(BASE_V7, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V7, "Solidworks")
RESULT_DIR     = os.path.join(BASE_V7, "Result")
DSD_DIR        = os.path.join(RESULT_DIR, "DSD")
OLHD_DIR       = os.path.join(RESULT_DIR, "OLHD")
GCI_DIR        = os.path.join(RESULT_DIR, "GCI")      # 캠페인 전 점검 (grid_convergence.py)

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_v7")   # .aedt 확장자 제외

# ── 1단계: DSD 선별 ──
DSD_PLAN_PATH      = os.path.join(DSD_DIR, "dsd_plan.csv")             # DSD.py 생성 (실험표)
DSD_RESULTS_PATH   = os.path.join(DSD_DIR, "results_dsd.csv")          # ML.py 관리
DSD_FAILED_PATH    = os.path.join(DSD_DIR, "failed_dsd.csv")           # ML.py 관리
DSD_EFFECTS_PATH   = os.path.join(DSD_DIR, "dsd_effects.csv")          # DSD_analysis.py 생성
SCREENING_PATH     = os.path.join(DSD_DIR, "screening_decision.json")  # DSD_analysis.py 생성

# ── 2단계: OLHD + 적응샘플링 ──
OLHD_PLAN_PATH      = os.path.join(OLHD_DIR, "olhd_plan.csv")        # OLHD.py 생성 (DOE 실험점, 처음 한 번)
OLHD_PLAN_META_PATH = os.path.join(OLHD_DIR, "olhd_plan_meta.json")  # 위 실험점을 만든 선별 조건
RESULTS_PATH = os.path.join(OLHD_DIR, "results_v7.csv")   # ML.py 관리, 실험 결과+예측값
FAILED_PATH  = os.path.join(OLHD_DIR, "failed_v7.csv")    # ML.py 관리, 실패점


def icepak_result_path(phase, idx):
    """Icepak Fields Summary 원본 CSV 경로 — 단계별 폴더/접두어를 분리해 섞이지 않게."""
    if phase == "dsd":
        return os.path.join(DSD_DIR, f"result_dsd_{idx:03d}.csv")
    if phase == "gci":
        return os.path.join(GCI_DIR, f"result_gci_{idx:03d}.csv")
    return os.path.join(OLHD_DIR, f"result_{idx:03d}.csv")


def step_path(phase, idx):
    os.makedirs(STEP_DIR, exist_ok=True)
    tag = f"{phase}_" if phase in ("dsd", "gci") else ""
    return os.path.join(STEP_DIR, f"flowpath_{tag}{idx:03d}.STEP")
