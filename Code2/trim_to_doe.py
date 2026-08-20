"""
results_v3.csv를 DOE 구간(idx < 80)만 남기고 새 파일로 재생성.

배경
  적응샘플링(idx 80~131)이 8차원 코너 쪽에 쏠려 비효율적이었던 게 확인되어,
  ML.py의 _gpr_suggest()를 고친 뒤(밀도 보정 + 수렴 지표 제외) idx 80부터
  다시 시작하기로 함. "최소 실험으로 수렴했다"를 깔끔한 숫자로 보여주기 위해
  코너 쏠림 구간(80~131)은 버리고 DOE(0~79)만 남김.

  summary_v3.csv는 result_parser.py에서 아예 생성하지 않도록 없앴음(사람이
  훑어보는 용도일 뿐 results_v3.csv가 같은 데이터를 다 갖고 있어 불필요했고,
  DRM이 걸려 다루기도 번거로웠음) — 그 파일 자체를 삭제하면 되고, 이 스크립트는
  더 이상 안 건드림.

사용법
  backup 폴더의 results_v3.csv를 읽어서, 같은 폴더에 results_v3_new.csv로
  DOE 80개만 저장.
  python trim_to_doe.py
"""
import os
import pandas as pd

# ── 여기 경로만 필요하면 바꾸기 ──
BACKUP_DIR = r"E:\Thermal_Anlaysis\Liquid_plate\260818\backup"
RESULTS_IN  = os.path.join(BACKUP_DIR, "results_v3.csv")
RESULTS_OUT = os.path.join(BACKUP_DIR, "results_v3_new.csv")

N_DOE = 80


def main():
    if not os.path.exists(RESULTS_IN):
        print(f"✗ 없음: {RESULTS_IN}")
        return
    df = pd.read_csv(RESULTS_IN)
    if "idx" not in df.columns:
        print("✗ idx 컬럼이 없음 — 원본 파일이 맞는지 확인 필요")
        return

    before = len(df)
    trimmed = df[df["idx"] < N_DOE].copy()
    trimmed.to_csv(RESULTS_OUT, index=False)
    print(f"✔ results_v3.csv: {before}행 -> {len(trimmed)}행 (idx < {N_DOE}) -> {RESULTS_OUT}")

    missing = set(range(N_DOE)) - set(trimmed["idx"].astype(int))
    if missing:
        print(f"  ⚠ idx 0~{N_DOE-1} 중 빠진 번호: {sorted(missing)} — DOE 구간에 실패점이 있었을 수 있음")

    print(
        "\n다음 단계(직접 수행):\n"
        "  1) 원본 results_v3.csv 삭제, summary_v3.csv도 삭제(더 이상 안 만듦)\n"
        "  2) results_v3_new.csv -> results_v3.csv 로 이름 변경\n"
        "  3) 이 파일을 실제 작업 폴더(Result)로 옮기기 — 지금은 backup 폴더에만 생성됨"
    )


if __name__ == "__main__":
    main()
