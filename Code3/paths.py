"""
V4 경로 설정 — 작업폴더 260821 (신규)

V3(260818)와 완전히 분리된 새 캠페인.
  · V3까지는 목적함수가 vel_cv_pass1/pass2(레인 유량의 변동계수)였는데,
    V4에서는 레인별 유량 14개를 각각 학습한다 — 이유는 ML.py 참고.
  · 레인별 원시값이 results_v3.csv에는 저장되지 않았으므로(CV로 압축된 값만 있음)
    V4는 idx=0부터 새로 시작한다. 단, 과거 Icepak 원본 CSV(result_NNN.csv)가
    남아있다면 seed_from_raw.py로 레인값을 복원해 재사용할 수 있다
    (CFD 재해석 없이 — 원본 CSV에 레인 14개 값이 전부 들어있음).

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\260818   (V3 — 원본 result CSV 복원용으로만 읽음)
    └─ Result         : result_000.csv ~ result_138.csv, results_v3.csv (읽기 전용)

  E:\\Thermal_Anlaysis\\Liquid_plate\\260821   (신규 — V4 작업폴더, 전부 여기)
    ├─ AEDT           : V4 전용 AEDT 프로젝트 저장 위치
    ├─ Code           : 이 코드(Code3 내용물)를 옮겨 넣는 위치
    ├─ Result         : V4 전용 결과 폴더 (results_v4.csv 등)
    └─ Solidworks     : 형상 모델 파일 (260821로 복사해 둘 것)
        └─ Step       : V4 전용 STEP 폴더

⚠ 시작 전 준비
  260821\\Solidworks 에 plate_base.SLDPRT, flowpath.SLDASM 을 복사해 둘 것.
  (260818 원본은 건드리지 않음 — 프로젝트/STEP 파일명이 idx 기준이라 폴더를 분리해야
   V3 산출물과 충돌하지 않음)
"""
import os

BASE_V3 = r"E:\Thermal_Anlaysis\Liquid_plate\260818"   # V3 — 원본 result CSV 복원용(읽기 전용)
BASE_V4 = r"E:\Thermal_Anlaysis\Liquid_plate\260821"   # 신규 — V4 작업폴더 (전부 여기)

AEDT_DIR       = os.path.join(BASE_V4, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V4, "Solidworks")
RESULT_DIR_V4  = os.path.join(BASE_V4, "Result")       # V4 전용 결과 폴더

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result (V4 전용 산출물) ──
ICEPAK_RESULT_DIR = RESULT_DIR_V4                                   # result_000.csv 등
RESULTS_PATH      = os.path.join(RESULT_DIR_V4, "results_v4.csv")   # ML.py 관리, 실험 결과+예측값
SUMMARY_PATH      = os.path.join(RESULT_DIR_V4, "summary_v4.csv")   # result_parser.py 관리, 요약
FAILED_PATH       = os.path.join(RESULT_DIR_V4, "failed_v4.csv")    # ML.py 관리, 실패점

# ── V3 결과 (seed_from_raw.py가 레인값 복원할 때만 참조, 읽기 전용) ──
V3_RESULT_DIR    = os.path.join(BASE_V3, "Result")
V3_RESULTS_PATH  = os.path.join(V3_RESULT_DIR, "results_v3.csv")    # idx → 설계변수 8개 대응표
