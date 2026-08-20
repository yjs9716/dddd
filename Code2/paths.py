"""
V3 경로 설정 — 260810은 오직 V2 결과(results_v2.csv, pass_cv_backfill.csv)를
시드용으로 읽어올 때만 참조하고, 그 외 모든 것(SolidWorks 모델, AEDT 프로젝트,
결과 기록, STEP 산출물)은 새 작업폴더 260818 밑에서 벌어진다.

  · DOE 80개만 V2에서 이어받고(seed_from_v2.py), 적응샘플링 284개는 이어받지 않음
    — 그 284개는 옛 목적함수(max(cv1,cv2))의 불확실성을 따라 골라진 경로라
      새 목적함수(cv1/cv2 분리) 학습에는 편향된 시드가 될 수 있어서 제외함.
      즉 V3의 새 실험은 idx=80부터 다시 시작됨.
  · SolidWorks 모델(plate_base.SLDPRT, flowpath.SLDASM)도 260818에 복사되어
    있으므로 그쪽을 참조함 (260810 원본은 건드리지 않음)
  · V3의 새 실험은 idx=80부터 다시 매겨지는데, V2도 이미 idx=80~363로
    result_080.csv~363.csv, flowpath_080.STEP~363.STEP을 만들어뒀으므로,
    작업폴더 자체를 260818로 분리해 원천적으로 충돌을 없앰
  · results_v2.csv / pass_cv_backfill.csv(260810)는 읽기만 하고 절대 안 건드림

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\260810   (기존 — V2 결과만 읽기 전용으로 참조)
    └─ Result         : results_v2.csv, pass_cv_backfill.csv (읽기 전용)

  E:\\Thermal_Anlaysis\\Liquid_plate\\260818   (신규 — V3 작업폴더, 전부 여기)
    ├─ AEDT           : V3 전용 AEDT 프로젝트 저장 위치
    ├─ Code           : 이 코드(Code2 내용물)를 옮겨 넣는 위치
    ├─ Result         : V3 전용 결과 폴더 (results_v3.csv 등)
    └─ Solidworks     : 형상 모델 파일 (260818로 복사된 것)
        └─ Step       : V3 전용 STEP 폴더
"""
import os

BASE_V2 = r"E:\Thermal_Anlaysis\Liquid_plate\260810"   # V2 결과 참조 전용 (읽기 전용)
BASE_V3 = r"E:\Thermal_Anlaysis\Liquid_plate\260818"   # 신규 — V3 작업폴더 (전부 여기)

AEDT_DIR       = os.path.join(BASE_V3, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V3, "Solidworks")
RESULT_DIR     = os.path.join(BASE_V2, "Result")         # V2 결과 — 읽기 전용 참조
RESULT_DIR_V3  = os.path.join(BASE_V3, "Result")         # V3 전용 결과 폴더

# ── SolidWorks ── (모델 파일도 260818로 복사된 것을 사용)
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result (V3 전용 산출물, 260818 밑) ──
ICEPAK_RESULT_DIR = RESULT_DIR_V3                                   # result_080.csv 등 (V3 전용, idx=80부터)
RESULTS_PATH      = os.path.join(RESULT_DIR_V3, "results_v3.csv")   # ML.py 관리, 실험 결과+예측값
FAILED_PATH       = os.path.join(RESULT_DIR_V3, "failed_v3.csv")    # ML.py 관리, 실패점

# ── V2 결과 (seed_from_v2.py가 DOE 80개만 초기 데이터로 읽어올 때만 참조, 260810) ──
V2_RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v2.csv")
V2_BACKFILL_CV_PATH  = os.path.join(RESULT_DIR, "pass_cv_backfill.csv")
