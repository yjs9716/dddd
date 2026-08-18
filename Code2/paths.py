"""
V3 경로 설정 — SolidWorks/AEDT "모델 파일"은 V2와 공유하지만, 실험마다 새로 생기는
산출물(STEP, Icepak 원본 CSV, 결과 기록)은 전용 폴더로 완전히 분리한다.

  · DOE 80개만 V2에서 이어받고(seed_from_v2.py), 적응샘플링 284개는 이어받지 않음
    — 그 284개는 옛 목적함수(max(cv1,cv2))의 불확실성을 따라 골라진 경로라
      새 목적함수(cv1/cv2 분리) 학습에는 편향된 시드가 될 수 있어서 제외함.
      즉 V3의 새 실험은 idx=80부터 다시 시작됨.
  · 그런데 V2도 idx=80부터 363까지 이미 result_080.csv~363.csv,
    flowpath_080.STEP~363.STEP을 만들어뒀음 — V3가 같은 idx로 새로 실험하면
    폴더를 공유할 경우 V2의 기존 파일을 덮어쓰게 됨.
    → 그래서 STEP_DIR / ICEPAK_RESULT_DIR을 V3 전용 하위폴더로 분리해 충돌을 원천 차단함
  · results_v2.csv / summary_v2.csv / pass_cv_backfill.csv는 읽기만 하고 절대 안 건드림

작업폴더: E:\\Thermal_Anlaysis\\Liquid_plate\\260810
  ├─ AEDT           : 해석 프로그램 파일 (V2와 공유)
  ├─ Code           : V2 코드 (건드리지 않음)
  ├─ Code2          : 이 코드 (V3 — vel_cv 분리 + max_temp 제외 + 종료기준 3%)
  ├─ Result         : V2 결과 (읽기 전용 참조) — results_v2.csv, pass_cv_backfill.csv
  ├─ Result_v3      : V3 전용 결과 폴더 (신규)
  ├─ Solidworks     : 형상 모델 파일 (V2와 공유)
  │   └─ Step       : V2 전용 STEP 폴더 (건드리지 않음)
  │   └─ Step_v3    : V3 전용 STEP 폴더 (신규)
"""
import os

BASE = r"E:\Thermal_Anlaysis\Liquid_plate\260810"

AEDT_DIR       = os.path.join(BASE, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE, "Solidworks")
RESULT_DIR     = os.path.join(BASE, "Result")           # V2 결과 — 읽기 전용 참조
RESULT_DIR_V3  = os.path.join(BASE, "Result_v3")         # V3 전용 결과 폴더

# ── SolidWorks ── (모델 파일 자체는 V2와 공유, STEP 산출물 폴더만 분리)
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step_v3")   # V3 전용 — V2의 Step 폴더와 절대 겹치지 않음

# ── AEDT ── (V2와 동일한 프로젝트 파일 공유)
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result (V3 전용 산출물) ──
ICEPAK_RESULT_DIR = RESULT_DIR_V3                                   # result_080.csv 등 (V3 전용, idx=80부터)
RESULTS_PATH      = os.path.join(RESULT_DIR_V3, "results_v3.csv")   # ML.py 관리, 실험 결과+예측값
SUMMARY_PATH      = os.path.join(RESULT_DIR_V3, "summary_v3.csv")   # result_parser.py 관리, 요약
FAILED_PATH       = os.path.join(RESULT_DIR_V3, "failed_v3.csv")    # ML.py 관리, 실패점

# ── V2 결과 (seed_from_v2.py가 DOE 80개만 초기 데이터로 읽어올 때만 참조) ──
V2_RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v2.csv")
V2_BACKFILL_CV_PATH  = os.path.join(RESULT_DIR, "pass_cv_backfill.csv")
