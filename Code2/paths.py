"""
V3 경로 설정 — Code(V2)와 물리적 파일(SolidWorks 모델, AEDT 프로젝트, Result 폴더)은
그대로 공유하고, 결과 기록 파일(results/summary/failed)만 별도 이름(_v3)으로 분리한다.
  · V2가 쓰던 results_v2.csv / summary_v2.csv / failed_v2.csv는 절대 건드리지 않음
  · result_XXX.csv(Icepak 원본)는 idx가 이어지므로(V2가 0~363까지 씀) 같은 폴더를
    그대로 써도 충돌 없음 — V3는 seed_from_v2.py로 기존 idx를 이어받고 새 실험은
    idx=364부터 시작함

작업폴더: E:\\Thermal_Anlaysis\\Liquid_plate\\260810
  ├─ AEDT        : 해석 프로그램 파일 (V2와 공유)
  ├─ Code        : V2 코드 (건드리지 않음)
  ├─ Code2       : 이 코드 (V3 — vel_cv 분리 + max_temp 제외 + 종료기준 3%)
  ├─ Result      : 매 해석마다 CSV 저장 (V2와 공유, 파일명만 v3로 분리)
  └─ Solidworks  : 형상변경할 모델 (V2와 공유)
"""
import os

BASE = r"E:\Thermal_Anlaysis\Liquid_plate\260810"

AEDT_DIR       = os.path.join(BASE, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE, "Solidworks")
RESULT_DIR     = os.path.join(BASE, "Result")

# ── SolidWorks ── (V2와 동일한 모델 파일 공유)
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")   # 실험점마다 STEP 저장

# ── AEDT ── (V2와 동일한 프로젝트 파일 공유)
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result ──
ICEPAK_RESULT_DIR = RESULT_DIR                              # result_000.csv 등 — V2와 같은 폴더, idx로 구분됨
RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v3.csv")   # ML.py 관리, 실험 결과+예측값 (V3 전용)
SUMMARY_PATH      = os.path.join(RESULT_DIR, "summary_v3.csv")   # result_parser.py 관리, 요약 (V3 전용)
FAILED_PATH       = os.path.join(RESULT_DIR, "failed_v3.csv")    # ML.py 관리, 실패점 (V3 전용)

# ── V2 결과 (seed_from_v2.py가 초기 데이터를 이어받을 때만 읽음) ──
V2_RESULTS_PATH      = os.path.join(RESULT_DIR, "results_v2.csv")
V2_BACKFILL_CV_PATH  = os.path.join(RESULT_DIR, "pass_cv_backfill.csv")
