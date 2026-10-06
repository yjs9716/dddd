"""
V6 경로 설정 — DSD 선별 → OLHD + GPR 적응샘플링 (1차/2차 핀뱅크 분리 11변수 후보)

V5(Code)와 완전히 분리된 새 캠페인.
  · 후보 설계변수 11개 = V5 9변수에서 핀(두께·개수)을 1차/2차 통과별로 분리.
  · 1단계 DSD(결정적 선별 설계) 29회로 영향이 없는 변수를 골라내 고정하고,
    2단계에서 남은 변수만으로 OLHD + IMSE 적응샘플링을 돌린다.
  · 형상이 달라졌으므로(핀뱅크별 독립 변수) V5 데이터를 재사용할 수 없다 —
    DSD run 0부터 새로 시작한다.

작업폴더 구조
  <BASE_V6>                (V6 작업폴더, 전부 여기)
    ├─ AEDT           : V6 전용 AEDT 프로젝트 저장 위치
    ├─ Code           : 이 코드(Code_DSD 폴더 내용물)를 옮겨 넣는 위치
    ├─ Result
    │   ├─ DSD        : 1단계 선별 — result_dsd_000.csv... (Icepak 원본)
    │   │               results_dsd.csv / failed_dsd.csv (ML.py 관리)
    │   │               dsd_effects.csv / screening_decision.json (DSD_analysis.py 생성)
    │   └─ OLHD       : 2단계 대리모델 — result_000.csv... (Icepak 원본)
    │                   results_v6.csv / failed_v6.csv (ML.py 관리)
    └─ Solidworks     : 형상 모델 파일
        └─ Step       : V6 전용 STEP 폴더

⚠ 시작 전 준비
  1) BASE_V6 아래 Solidworks 폴더에 plate_base.SLDPRT, flowpath.SLDASM 을 복사해 둘 것.
  2) SolidWorks Equation Manager에 아래 **후보변수 11개**가 전부 전역변수로 있어야 한다
     (이름 정확히 일치 — 1단계에서 선별로 고정된 변수도 매 회차 파이썬이 고정값을
      써넣으므로 2단계에서도 전역변수로 남겨둘 것):
       input_thick, input_angle, power_input_thick, mid_thick, mid_angle,
       mid_input_thick, output_thick,
       fin_thick_1, fin_count_1, fin_thick_2, fin_count_2
     핀 간격은 뱅크별로 수식으로 걸어둘 것:
       "fin_gap_1" = (86.5 - "fin_count_1" * "fin_thick_1") / ("fin_count_1" + 1)
       "fin_gap_2" = (86.5 - "fin_count_2" * "fin_thick_2") / ("fin_count_2" + 1)
     1차 뱅크 핀 선형패턴은 fin_*_1, 2차 뱅크 핀 선형패턴은 fin_*_2 에 묶는다
     (패턴 간격 = 갭 + 두께, 인스턴스 개수 = 개수, 첫 핀 오프셋 = 갭).
  3) power_output_thick(25mm), fin_height(8.0mm)는 V5와 같이 스케치에 직접 숫자로 둔다.

테스트용: 환경변수 DSD_CAMPAIGN_DIR 을 주면 BASE_V6 대신 그 폴더를 쓴다
(실제 캠페인에서는 설정하지 말 것).
"""
import os

BASE_V6 = os.environ.get("DSD_CAMPAIGN_DIR",
                         r"E:\Thermal_Anlaysis\Liquid_plate\V6_DSD")   # ⚠ 실제 작업폴더로 바꿀 것

AEDT_DIR       = os.path.join(BASE_V6, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V6, "Solidworks")
RESULT_DIR     = os.path.join(BASE_V6, "Result")
DSD_DIR        = os.path.join(RESULT_DIR, "DSD")
OLHD_DIR       = os.path.join(RESULT_DIR, "OLHD")

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── 1단계: DSD 선별 ──
DSD_PLAN_PATH      = os.path.join(DSD_DIR, "dsd_plan.csv")             # DSD.py 생성 (실험표)
DSD_RESULTS_PATH   = os.path.join(DSD_DIR, "results_dsd.csv")          # ML.py 관리
DSD_FAILED_PATH    = os.path.join(DSD_DIR, "failed_dsd.csv")           # ML.py 관리
DSD_EFFECTS_PATH   = os.path.join(DSD_DIR, "dsd_effects.csv")          # DSD_analysis.py 생성
SCREENING_PATH     = os.path.join(DSD_DIR, "screening_decision.json")  # DSD_analysis.py 생성

# ── 2단계: OLHD + 적응샘플링 ──
RESULTS_PATH = os.path.join(OLHD_DIR, "results_v6.csv")   # ML.py 관리, 실험 결과+예측값
FAILED_PATH  = os.path.join(OLHD_DIR, "failed_v6.csv")    # ML.py 관리, 실패점


def icepak_result_path(phase, idx):
    """Icepak Fields Summary 원본 CSV 경로 — 단계별 폴더/접두어를 분리해 섞이지 않게."""
    if phase == "dsd":
        return os.path.join(DSD_DIR, f"result_dsd_{idx:03d}.csv")
    return os.path.join(OLHD_DIR, f"result_{idx:03d}.csv")


def step_path(phase, idx):
    os.makedirs(STEP_DIR, exist_ok=True)
    tag = "dsd_" if phase == "dsd" else ""
    return os.path.join(STEP_DIR, f"flowpath_{tag}{idx:03d}.STEP")
