"""
V2 유로 7변수 — Icepak 결과 CSV 파싱

V1 대비 변경점
  - summary 컬럼: angle/thickness 2개 → 7개 파라미터
  - 반환값: 튜플 → dict (목적함수 후보를 늘려도 호출부가 안 깨지도록)
  - CSV 행 구조 자체는 V1과 동일 (형상만 바뀌고 측정 항목은 그대로이므로)
"""
import os

import pandas as pd

from OLHD import PARAM_NAMES
from paths import SUMMARY_PATH

_SUMMARY_COLS = (["idx"] + PARAM_NAMES
                 + ["pressure_drop", "vel_cv", "max_temp", "temp_std"])


def extract_and_save(idx, params, result_path):
    """
    CSV 한 장 구조 (skiprows=5 이후):
      행 0~18  : source1~19 온도 (I열=최대, J열=평균)
      행 19    : Fan1_Passage 차압 (J열)
      행 20~49 : V_inlet_01~30 입구 속도 (J열, -X방향 성분 Reduced)

    반환: {"max_temp":…, "temp_std":…, "pressure_drop":…, "vel_cv":…}
    """
    df = pd.read_csv(result_path, header=None, skiprows=5, on_bad_lines="skip")

    temp_rows  = df.iloc[0:19]
    max_temps  = temp_rows[8].astype(float).tolist()
    mean_temps = temp_rows[9].astype(float).tolist()
    pressure_drop = float(df.iloc[19, 9])

    overall_max_temp = max(max_temps)
    temp_std         = pd.Series(mean_temps).std()

    # 레인별 속도 30개 → CV (모집단 std / 평균 × 100, 엑셀 STDEV.P 기준)
    speeds = df.iloc[20:50, 9].astype(float)
    if len(speeds) != 30:
        raise ValueError(f"레인 속도 30개 기대, {len(speeds)}개 파싱됨 — CSV 행 구조 확인 필요")
    vel_cv = float(speeds.std(ddof=0) / speeds.mean() * 100)

    results = {
        "max_temp":      overall_max_temp,
        "temp_std":      temp_std,
        "pressure_drop": pressure_drop,
        "vel_cv":        vel_cv,
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

    print(f"[{idx}] 차압:{pressure_drop} 속도CV:{vel_cv:.4f}% "
          f"(기록용 — 최대온도:{overall_max_temp} 온도std:{temp_std})")
    return results
