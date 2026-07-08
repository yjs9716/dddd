# 후처리: 속도 CSV export + 파싱(CV 계산) + 기존 결과 CSV 파싱(온도/차압)
import numpy as np
import pandas as pd

from sheets import N_LANES, PREFIX

SPEED_DIR = r"E:\Thermal_Anlaysis\Results"

# Fields Summary CSV에서 Mean 값이 있는 열 인덱스 (기존 result CSV와 동일 포맷 가정)
# ※ 첫 실행 후 speed_000.csv를 열어 Mean 열 위치가 맞는지 반드시 확인할 것
MEAN_COL = 9


def export_speed_csv(oDesign, idx):
    """30개 시트의 Speed 요약을 speed_{idx:03d}.csv로 export.
    run_icepak()의 온도/차압 export가 끝난 뒤 호출할 것
    (EditFieldsSummarySetting은 설정을 통째로 교체하므로 순서 중요)."""
    speed_path = rf"{SPEED_DIR}\speed_{idx:03d}.csv"

    setting = [
        "SolutionName:=", "Setup1 : SteadyState",
        "Variation:=", "Nominal",
    ]
    for i in range(1, N_LANES + 1):
        setting += [
            "Calculation:=",
            ["Object", "Surface", f"{PREFIX}_{i:02d}", "Speed", "", "Default", "All", "Nominal", True],
        ]

    oModule = oDesign.GetModule("Solutions")
    oModule.EditFieldsSummarySetting(setting)
    oModule.ExportFieldsSummary(
        [
            "SolutionName:=", "Setup1 : SteadyState",
            "DesignVariationKey:=", "Nominal",
            "ExportFileName:=", speed_path,
            "IntrinsicValue:=", "",
        ])
    print(f"[{idx}] 속도 CSV 저장 완료: {speed_path}")
    return speed_path


def parse_speed_csv(speed_path):
    """speed CSV에서 30개 레인 평균유속 추출 → (speeds, cv_percent).
    CV는 모집단 표준편차(STDEV.P) / 평균 × 100 — 엑셀 수동 계산과 동일 기준."""
    df = pd.read_csv(speed_path, header=None, skiprows=5, on_bad_lines="skip")
    speeds = df.iloc[0:N_LANES, MEAN_COL].astype(float).to_numpy()

    if len(speeds) != N_LANES:
        raise ValueError(f"레인 속도 {N_LANES}개 기대, {len(speeds)}개 파싱됨 — CSV 포맷/MEAN_COL 확인 필요")

    cv_percent = float(np.std(speeds, ddof=0) / np.mean(speeds) * 100)
    print(f"레인 평균유속 {len(speeds)}개, CV = {cv_percent:.4f}%")
    return speeds, cv_percent


def parse_result_csv(result_path):
    """기존 result_{idx}.csv에서 (max_temp, temp_std, pressure_drop) 추출.
    result_parser.extract_and_save와 동일 로직이나 summary.xlsx 기록은 안 함
    (이번 캠페인 기록은 results_ps.csv 하나로 통일)."""
    df = pd.read_csv(result_path, header=None, skiprows=5, on_bad_lines="skip")
    temp_rows     = df.iloc[0:19]
    max_temps     = temp_rows[8].astype(float).tolist()
    mean_temps    = temp_rows[9].astype(float).tolist()
    pressure_drop = float(df.iloc[19, 9])

    overall_max_temp = max(max_temps)
    temp_std         = float(pd.Series(mean_temps).std())
    return overall_max_temp, temp_std, pressure_drop
