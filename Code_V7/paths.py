"""
V7 경로 설정 — V6 선별(DSD) 결과를 이어받아 OLHD + GPR 적응샘플링을 새로 돈다

V6 대비 바뀐 것
  · 발열: FR-4 블록(부피 발열) → 슬롯 바닥 접촉면 2D 면 발열(Total Power 40 W). 지표가 온도 셋으로 바뀌어
    V6 결과(results_v6.csv)와 섞이면 안 되므로 작업폴더 자체를 따로 둔다.
  · DSD 단계는 다시 하지 않는다. V6 의 screening_decision.json(활성 8변수, 고정 3변수)을 그대로 쓴다.

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\V7   (V7 작업폴더, 전부 여기)
    ├─ AEDT           : V7 AEDT 프로젝트 저장 위치
    ├─ Code           : 이 코드(Code_V7 폴더 내용물)를 옮겨 넣는 위치
    ├─ Result
    │   ├─ screening_decision.json   ← V6 Result\\DSD 에서 복사 (필수)
    │   ├─ OLHD       : result_000.csv... (Icepak 원본), results_v7.csv / failed_v7.csv (ML.py 관리)
    │   │               olhd_plan.csv / olhd_plan_meta.json ← V6 Result\\OLHD 에서 복사 권장
    │   │               (복사하면 V6 와 같은 80점을 돌려 두 버전을 점대점으로 비교할 수 있다.
    │   │                없으면 같은 규칙·같은 시드로 새로 만든다 — 결과는 같아야 한다)
    │   ├─ GCI        : 캠페인 전 점검 (grid_convergence.py)
    │   └─ VERIFY     : 검증 해석 (verify_point.py)
    └─ Solidworks     : plate_base.SLDPRT, flowpath.SLDASM ← V6 Solidworks 에서 복사 (형상·전역변수 그대로)
        └─ Step

⚠ 시작 전 준비
  1) 위 세 가지(screening_decision.json, SolidWorks 두 파일, 원하면 olhd_plan 두 파일)를 복사해 둘 것.
  2) SolidWorks Equation Manager 의 전역변수와 수식은 V6 그대로다 — 후보 11개가 전부 전역변수로 있어야 한다
     (선별로 고정된 3변수도 매 회차 파이썬이 고정값을 써넣는다):
       input_thick, input_angle, power_input_thick, mid_thick, mid_angle,
       mid_input_thick, output_thick,
       fin_thick_1, fin_count_1, fin_thick_2, fin_count_2
     핀 간격 수식:
       "fin_gap_1" = (86.5 - "fin_count_1" * "fin_thick_1") / ("fin_count_1" + 1)
       "fin_gap_2" = (86.5 - "fin_count_2" * "fin_thick_2") / ("fin_count_2" + 1)

테스트용: 환경변수 V7_CAMPAIGN_DIR 을 주면 BASE_V7 대신 그 폴더를 쓴다 (실제 캠페인에서는 설정하지 말 것).
"""
import os

BASE_V7 = os.environ.get("V7_CAMPAIGN_DIR",
                         r"E:\Thermal_Anlaysis\Liquid_plate\V7")   # V7 작업폴더

AEDT_DIR       = os.path.join(BASE_V7, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V7, "Solidworks")
RESULT_DIR     = os.path.join(BASE_V7, "Result")
OLHD_DIR       = os.path.join(RESULT_DIR, "OLHD")
GCI_DIR        = os.path.join(RESULT_DIR, "GCI")      # 캠페인 전 점검 (grid_convergence.py)

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_v7")   # .aedt 확장자 제외

# ── 선별 결과 (V6 DSD 에서 복사) ──
SCREENING_PATH = os.path.join(RESULT_DIR, "screening_decision.json")

# ── OLHD + 적응샘플링 ──
OLHD_PLAN_PATH      = os.path.join(OLHD_DIR, "olhd_plan.csv")        # OLHD.py 생성 (DOE 실험점, 처음 한 번)
OLHD_PLAN_META_PATH = os.path.join(OLHD_DIR, "olhd_plan_meta.json")  # 위 실험점을 만든 선별 조건
RESULTS_PATH = os.path.join(OLHD_DIR, "results_v7.csv")   # ML.py 관리, 실험 결과+예측값
FAILED_PATH  = os.path.join(OLHD_DIR, "failed_v7.csv")    # ML.py 관리, 실패점


def icepak_result_path(phase, idx):
    """Icepak Fields Summary 원본 CSV 경로 — 단계별 폴더/접두어를 분리해 섞이지 않게."""
    if phase == "gci":
        return os.path.join(GCI_DIR, f"result_gci_{idx:03d}.csv")
    return os.path.join(OLHD_DIR, f"result_{idx:03d}.csv")


def step_path(phase, idx):
    os.makedirs(STEP_DIR, exist_ok=True)
    tag = f"{phase}_" if phase == "gci" else ""
    return os.path.join(STEP_DIR, f"flowpath_{tag}{idx:03d}.STEP")
