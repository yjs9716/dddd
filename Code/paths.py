"""
V2 공통 경로 설정 — 작업폴더 구조가 바뀌면 이 파일만 고치면 됨.

작업폴더: E:\\Thermal_Anlaysis\\Liquid_plate\\260810
  ├─ AEDT        : 해석 프로그램 파일
  ├─ Code        : 코드 (이 파일들이 저장되는 곳)
  ├─ Result      : 매 해석마다 CSV 저장
  └─ Solidworks  : 형상변경할 모델
"""
import os

BASE = r"E:\Thermal_Anlaysis\Liquid_plate\260810"

AEDT_DIR       = os.path.join(BASE, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE, "Solidworks")
RESULT_DIR     = os.path.join(BASE, "Result")

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")   # 실험점마다 STEP 저장

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result ──
ICEPAK_RESULT_DIR = RESULT_DIR                              # result_000.csv 등 (Icepak 원본)
RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v2.csv")   # ML.py 관리, 실험 결과+예측값
SUMMARY_PATH      = os.path.join(RESULT_DIR, "summary_v2.csv")   # result_parser.py 관리, 요약
FAILED_PATH       = os.path.join(RESULT_DIR, "failed_v2.csv")    # ML.py 관리, 실패점
