"""
V2 유로 7변수 — Icepak 결과 CSV 파싱

V1 대비 변경점
  - summary 컬럼: angle/thickness 2개 → 7개 파라미터
  - 반환값: 튜플 → dict (목적함수 후보를 늘려도 호출부가 안 깨지도록)
  - 전원공급모듈 온도(행 50) 신규 파싱 — icepak.py의 Fields Summary 맨 뒤에 추가한 항목
  - temp_std가 이제 목적함수로 승격 (ML.py OBJECTIVES 참고) — 여기서는 값 계산까지만,
    OBJECTIVES/RECORD_ONLY 분류는 ML.py 쪽 책임
"""
import os

import pandas as pd

from OLHD import PARAM_NAMES
from paths import SUMMARY_PATH

_SUMMARY_COLS = (["idx"] + PARAM_NAMES
                 + ["pressure_drop", "vel_cv", "temp_std", "power_module_temp", "max_temp"])


def extract_and_save(idx, params, result_path):
    """
    CSV 한 장 구조 (skiprows=5 이후):
      행 0~18  : source1~19 온도 (I열=최대, J열=평균)
      행 19    : Fan1_Passage 차압 (J열)
      행 20~49 : V_inlet_01~30 입구 속도 (J열, -X방향 성분 Reduced)
      행 50    : power_module 온도 (I열=최대, 단일 블록이라 I열 그대로 사용) — 신규

    반환: {"pressure_drop":…, "vel_cv":…, "temp_std":…, "power_module_temp":…, "max_temp":…}
    """
    df = pd.read_csv(result_path, header=None, skiprows=5, on_bad_lines="skip")

    temp_rows  = df.iloc[0:19]
    max_temps  = temp_rows[8].astype(float).tolist()
    mean_temps = temp_rows[9].astype(float).tolist()
    pressure_drop = float(df.iloc[19, 9])

    overall_max_temp = max(max_temps)
    temp_std         = float(pd.Series(mean_temps).std())

    # 레인별 속도 30개 → CV (모집단 std / 평균 × 100, 엑셀 STDEV.P 기준)
    speeds = df.iloc[20:50, 9].astype(float)
    if len(speeds) != 30:
        raise ValueError(f"레인 속도 30개 기대, {len(speeds)}개 파싱됨 — CSV 행 구조 확인 필요")
    vel_cv = float(speeds.std(ddof=0) / speeds.mean() * 100)

    if len(df) <= 50:
        raise ValueError(
            "전원모듈 온도(행 50)가 없음 — icepak.py의 summary_setting에 "
            "power_module Calculation이 빠졌거나 순서가 바뀌었는지 확인"
        )
    power_module_temp = float(df.iloc[50, 8])   # 단일 블록 → 최대(I열) = 대표값

    results = {
        "pressure_drop":     pressure_drop,
        "vel_cv":            vel_cv,
        "temp_std":          temp_std,
        "power_module_temp": power_module_temp,
        "max_temp":          overall_max_temp,   # 기록용 (스크리닝) — 목적함수 아님
    }

    # ── summary 누적 저장 ──
    if os.path.exists(SUMMARY_PATH):
        try:
            df_summary = pd.read_csv(SUMMARY_PATH)
        except Exception as e:
            # 기존 파일 손상 — results_v2.csv(ML.py 관리)가 같은 데이터를 보관 중이라
            # 요약본은 새로 시작해도 데이터 손실 없음
            print(f"[{idx}] summary_v2.csv 손상 감지({e}) — 새로 시작합니다")
            df_summary = pd.DataFrame(columns=_SUMMARY_COLS)
    else:
        df_summary = pd.DataFrame(columns=_SUMMARY_COLS)

    row = {"idx": idx}
    row.update(params)
    row.update(results)
    df_summary = pd.concat([df_summary, pd.DataFrame([row])], ignore_index=True)
    df_summary.to_csv(SUMMARY_PATH, index=False)

    print(f"[{idx}] 차압:{pressure_drop}  속도CV:{vel_cv:.4f}%  "
          f"온도std:{temp_std:.4f}  전원모듈온도:{power_module_temp:.2f}  "
          f"(기록용 최고온도:{overall_max_temp})")
    return results
