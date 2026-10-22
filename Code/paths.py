"""
V5 경로 설정 — 작업폴더 260827 (신규)

V4(260821)와 완전히 분리된 새 캠페인.
  · 설계변수가 8개 → 9개로 바뀌었다(power_output_thick·fin_height 고정, 방열핀
    2변수 fin_thick/fin_count 신규).
  · 목적함수의 레인 측정도 14개 → std 2개(통과별 유로 전체의 표준편차)로 바뀌었다
    — 유로 자체는 전부(fin_count+1개) 재지만, GPR엔 압축된 값만 넘긴다.
  · 형상 자체가 달라졌으므로(핀뱅크 길이 66.5 → 86.5mm 전제) V4 데이터를 재사용할
    수 없다 — seed_from_raw 같은 복원 경로 없이 idx=0부터 새로 시작한다.

작업폴더 구조
  E:\\Thermal_Anlaysis\\Liquid_plate\\260827   (V5 작업폴더, 전부 여기)
    ├─ AEDT           : V5 전용 AEDT 프로젝트 저장 위치
    ├─ Code           : 이 코드(이 폴더 내용물)를 옮겨 넣는 위치
    ├─ Result         : result_000.csv... (Icepak Fields Summary 원본) +
    │                   results_v5.csv / failed_v5.csv (ML.py가 관리)
    └─ Solidworks     : 형상 모델 파일
        └─ Step       : V5 전용 STEP 폴더

⚠ 시작 전 준비
  1) 260827\\Solidworks 에 plate_base.SLDPRT, flowpath.SLDASM 을 복사해 둘 것.
  2) SolidWorks Equation Manager에 아래 **자유변수 9개**가 전부 있어야 한다
     (이름 정확히 일치 — 파이썬이 매 회차 이 이름으로 찾아서 값을 써넣는다):
       input_thick, input_angle, power_input_thick, mid_thick, mid_angle,
       mid_input_thick, output_thick, fin_thick, fin_count
     그리고 핀 간격은 변수가 아니라 수식으로 걸어둘 것:
       "fin_gap" = (86.5 - "fin_count" * "fin_thick") / ("fin_count" + 1)
     핀은 선형패턴으로 만들고, 패턴 간격 = "fin_gap" + "fin_thick",
     인스턴스 개수 = "fin_count", 첫 핀의 상단벽 오프셋 = "fin_gap" 으로 묶으면
     상단벽↔핀 / 핀↔핀 / 핀↔하단벽 간격이 전부 자동으로 같아진다.
  3) power_output_thick(25mm), fin_height(8.0mm — 유로 깊이와 동일, 우회공간
     없음)는 **이름 붙은 전역변수로 만들지 말고 스케치에 직접 숫자로 넣어둘 것**.
     캠페인 내내 안 바뀌는 값이라 파이썬이 매 회차 값을 써넣을 필요가 없다
     (Solidworks.py는 이 두 값을 아예 안 건드림). 실제 제작 시엔 fin_height만
     조립공차 위해 7.5mm로 수작업으로 낮춰서 최종 1회 재검증한다.
"""
import os

BASE_V5 = r"E:\Thermal_Anlaysis\Liquid_plate\260827"   # V5 작업폴더 (전부 여기)

AEDT_DIR       = os.path.join(BASE_V5, "AEDT")
SOLIDWORKS_DIR = os.path.join(BASE_V5, "Solidworks")
RESULT_DIR_V5  = os.path.join(BASE_V5, "Result")

# ── SolidWorks ──
PART_PATH = os.path.join(SOLIDWORKS_DIR, "plate_base.SLDPRT")
ASM_PATH  = os.path.join(SOLIDWORKS_DIR, "flowpath.SLDASM")
STEP_DIR  = os.path.join(SOLIDWORKS_DIR, "Step")

# ── AEDT ──
AEDT_PROJ_PATH = os.path.join(AEDT_DIR, "thermal_test")   # .aedt 확장자 제외

# ── Result (V5 전용 산출물) ──
ICEPAK_RESULT_DIR = RESULT_DIR_V5                                   # result_000.csv ...
RESULTS_PATH      = os.path.join(RESULT_DIR_V5, "results_v5.csv")   # ML.py 관리, 실험 결과+예측값
FAILED_PATH       = os.path.join(RESULT_DIR_V5, "failed_v5.csv")    # ML.py 관리, 실패점
