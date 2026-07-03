import pandas as pd
import os

SUMMARY_PATH = r"E:\Thermal_Anlaysis\summary.xlsx"

def extract_and_save(idx, angle, thickness, result_path):
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

    if os.path.exists(SUMMARY_PATH):
        df_summary = pd.read_excel(SUMMARY_PATH)
    else:
        df_summary = pd.DataFrame(columns=["idx", "angle", "thickness", "max_temp", "temp_std", "pressure_drop"])

    new_row = {
        "idx": idx,
        "angle": angle,
        "thickness": thickness,
        "max_temp": overall_max_temp,
        "temp_std": temp_std,
        "pressure_drop": pressure_drop
    }
    df_summary = pd.concat([df_summary, pd.DataFrame([new_row])], ignore_index=True)
    df_summary.to_excel(SUMMARY_PATH, index=False)
    print(f"[{idx}] 최대온도:{overall_max_temp} 온도std:{temp_std} 차압:{pressure_drop}")
    return overall_max_temp, temp_std, pressure_drop
