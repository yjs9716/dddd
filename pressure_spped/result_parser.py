import pandas as pd
import os

SUMMARY_PATH = r"E:\Thermal_Anlaysis\summary_ps.xlsx"

def extract_and_save(idx, angle, thickness, result_path):
    # CSV 한 장 구조 (skiprows=5 이후):
    #   행 0~18  : source1~19 온도 (I열=최대, J열=평균)
    #   행 19    : Fan1_Passage 차압 (J열)
    #   행 20~49 : V_inlet_01~30 입구 속도 (J열, -X방향 성분 Reduced)
    df = pd.read_csv(
        result_path,
        header=None,
        skiprows=5,
        on_bad_lines='skip'
    )
    temp_rows     = df.iloc[0:19]
    max_temps     = temp_rows[8].astype(float).tolist()
    mean_temps    = temp_rows[9].astype(float).tolist()
    pressure_drop = float(df.iloc[19, 9])

    overall_max_temp = max(max_temps)
    temp_std         = pd.Series(mean_temps).std()

    # 레인별 속도 30개 → CV (모집단 std / 평균 × 100, 엑셀 STDEV.P 기준과 동일)
    speeds = df.iloc[20:50, 9].astype(float)
    if len(speeds) != 30:
        raise ValueError(f"레인 속도 30개 기대, {len(speeds)}개 파싱됨 — CSV 행 구조 확인 필요")
    vel_cv = float(speeds.std(ddof=0) / speeds.mean() * 100)

    if os.path.exists(SUMMARY_PATH):
        df_summary = pd.read_excel(SUMMARY_PATH)
    else:
        df_summary = pd.DataFrame(columns=["idx", "angle", "thickness",
                                           "pressure_drop", "vel_cv", "max_temp", "temp_std"])

    new_row = {
        "idx": idx,
        "angle": angle,
        "thickness": thickness,
        "pressure_drop": pressure_drop,
        "vel_cv": vel_cv,
        "max_temp": overall_max_temp,
        "temp_std": temp_std
    }
    df_summary = pd.concat([df_summary, pd.DataFrame([new_row])], ignore_index=True)
    df_summary.to_excel(SUMMARY_PATH, index=False)
    print(f"[{idx}] 차압:{pressure_drop} 속도CV:{vel_cv:.4f}% (기록용 — 최대온도:{overall_max_temp} 온도std:{temp_std})")
    return overall_max_temp, temp_std, pressure_drop, vel_cv
