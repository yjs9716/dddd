"""
V3 경로 설정 — SolidWorks/AEDT "모델 파일"과 V2 결과(시드 참조용)는 기존
260810 폴더에 그대로 두고, V3가 새로 만들어내는 산출물(STEP, Icepak 원본 CSV,
결과 기록)만 새 작업폴더 260818 밑에 쌓이게 한다.

  · DOE 80개만 V2에서 이어받고(seed_from_v2.py), 적응샘플링 284개는 이어받지 않음
    — 그 284개는 옛 목적함수(max(cv1,cv2))의 불확실성을 따라 골라진 경로라
      새 목적함수(cv1/cv2 분리) 학습에는 편향된 시드가 될 수 있어서 제외함.
      즉 V3의 새 실험은 idx=80부터 다시 시작됨.
  · SolidWorks 모델(plate_base.SLDPRT, flowpath.SLDASM)과 AEDT 프로젝트
    (thermal_test.aedt)는 형상 자체가 바뀐 게 아니므로 260810에 있는 걸 그대로 씀
    — 굳이 복사할 필요 없음
  · V3의 새 실험은 idx=80부터 다시 매겨지는데, V2도 이미 idx=80~363로
    result_080.csv~363.csv, flowpath_080.STEP~363.STEP을 만들어뒀으므로,
    폴더 자체를 260818로 분리해 원천적으로 충돌을 없앰
  · results_v2.csv / pass_cv_backfill.csv(260810)는 읽기만 하고 절대 안 건드림

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\260810   (기존 — V2, 읽기 전용으로만 참조)
    ├─ AEDT           : 해석 프로그램 파일 (V3도 그대로 사용)
    ├─ Code           : V2 코드 (건드리지 않음)
    ├─ Result         : V2 결과 — results_v2.csv, pass_cv_backfill.csv (읽기 전용)
    └─ Solidworks     : 형상 모델 파일 (V3도 그대로 사용)
        └─ Step       : V2 전용 STEP 폴더 (건드리지 않음)

  E:\\Thermal_Anlaysis\\Liquid_plate\\260818   (신규 — V3 산출물 전용)
    ├─ Code2          : 이 코드
    ├─ Result         : V3 전용 결과 폴더 (results_v3.csv, summary_v3.csv 등)
    └─ Step           : V3 전용 STEP 폴더
"""
import os

BASE_V2 = r"E:\Thermal_Anlaysis\Liquid_plate\260810"   # 기존 — 모델 파일 + V2 결과(읽기 전용)
BASE_V3 = r"E:\Thermal_Anlaysis\Liquid_plate\260818"   # 신규 — V3 산출물 전용

AEDT_DIR       = os.path.join(BASE_V2, "AEDT")           # V2와 공유 (그대로 사용)
SOLIDWORKS_DIR = os.path.join(BASE_V2, "Solidworks")     # V2와 공유 (그대로 사용)
RESULT_DIR     = os.path.join(BASE_V2, "Result")         # V2 결과 — 읽기 전용 참조
RESULT_DIR_V3  = os.path.join(BASE_V3, "Result")         # V3 전용 결과 폴더 (새 작업폴더 밑)

# ── SolidWorks ── (모델 파일은 260810 것을 그대로 사용, STEP 산출물만 260818로 분리)
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(BASE_V3, "Solidworks", "Step")   # V3 전용 — V2의 Step 폴더와 절대 겹치지 않음

# ── AEDT ── (프로젝트 파일은 260810 것을 그대로 사용)
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result (V3 전용 산출물, 260818 밑) ──
ICEPAK_RESULT_DIR = RESULT_DIR_V3                                   # result_080.csv 등 (V3 전용, idx=80부터)
RESULTS_PATH      = os.path.join(RESULT_DIR_V3, "results_v3.csv")   # ML.py 관리, 실험 결과+예측값
SUMMARY_PATH      = os.path.join(RESULT_DIR_V3, "summary_v3.csv")   # result_parser.py 관리, 요약
FAILED_PATH       = os.path.join(RESULT_DIR_V3, "failed_v3.csv")    # ML.py 관리, 실패점

# ── V2 결과 (seed_from_v2.py가 DOE 80개만 초기 데이터로 읽어올 때만 참조, 260810) ──
V2_RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v2.csv")
V2_BACKFILL_CV_PATH  = os.path.join(RESULT_DIR, "pass_cv_backfill.csv")
