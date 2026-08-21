"""
V3의 Icepak 원본 CSV에서 레인별 유량을 복원해 results_v4.csv를 만든다 (CFD 재해석 없이).

왜 이게 가능한가
  V3의 results_v3.csv에는 레인 유량이 CV(vel_cv_pass1/pass2)로 압축된 값만
  남아 있어서 레인별 값을 되살릴 수 없다. 그런데 Icepak이 내보낸 원본
  Fields Summary CSV(result_000.csv ~ result_NNN.csv)에는 레인 14개 값이
  그대로 들어있다 — icepak.py가 처음부터 전부 export하고 있었고,
  V3의 result_parser.py가 그걸 읽어서 CV로 압축한 뒤 버렸을 뿐이다.

  따라서 그 원본 CSV들이 260818\\Result 에 아직 남아있다면, CFD를 다시 돌리지 않고
  레인별 유량을 복원해 V4의 학습 데이터로 쓸 수 있다. (설계변수 8개와 중량은
  results_v3.csv에서 가져온다 — 중량은 SolidWorks 값이라 원본 CSV에 없음)

사용법
  python seed_from_raw.py            # 무엇이 복원 가능한지 확인만 (파일 안 씀)
  python seed_from_raw.py --write    # 실제로 results_v4.csv 생성

  ⚠ --write는 기존 results_v4.csv가 있으면 중단한다. 덮어쓰려면 직접 지울 것.

복원이 안 되는 경우
  원본 CSV가 지워졌으면 이 스크립트는 아무것도 못 한다 — 그때는 main.py를
  그냥 돌려서 DOE 80점부터 새로 해석하면 된다.
"""
import os
import sys

import numpy as np
import pandas as pd

from OLHD import PARAM_NAMES
from paths import RESULTS_PATH, V3_RESULT_DIR, V3_RESULTS_PATH
from result_parser import (LANE1_NAMES, LANE2_NAMES, _lane_flows_lpm, _cv_from_flows,
                           _area_m2, ROW_SOURCE, ROW_DP, ROW_LANE1, ROW_LANE2,
                           ROW_PMFLOW, N_ROWS, COL_MAX, COL_MEAN, COL_AREA,
                           TOTAL_FLOW_LPM)
from icepak import N_SOURCE
from ML import _COLUMNS, MODELED_NAMES


def _parse_raw(path):
    """원본 Fields Summary CSV 한 장 → 지표 dict (중량 제외 — SolidWorks 값이라 여기 없음)"""
    df = pd.read_csv(path, header=None, skiprows=5, sep=None, engine="python",
                     on_bad_lines="skip")
    if len(df) < N_ROWS:
        raise ValueError(f"행이 {len(df)}개뿐 ({N_ROWS}개 기대)")

    temp_rows = df.iloc[ROW_SOURCE:ROW_SOURCE + N_SOURCE]
    out = {
        "max_temp":      float(temp_rows[COL_MAX].astype(float).max()),
        "temp_std":      float(temp_rows[COL_MEAN].astype(float).std(ddof=0)),
        "pressure_drop": float(df.iloc[ROW_DP, COL_MEAN]),
    }

    flows1 = _lane_flows_lpm(df, ROW_LANE1)
    flows2 = _lane_flows_lpm(df, ROW_LANE2)
    out.update({n: float(v) for n, v in zip(LANE1_NAMES, flows1)})
    out.update({n: float(v) for n, v in zip(LANE2_NAMES, flows2)})
    out["vel_cv_pass1"] = _cv_from_flows(flows1)
    out["vel_cv_pass2"] = _cv_from_flows(flows2)

    pm_speed = abs(float(df.iloc[ROW_PMFLOW, COL_MEAN]))
    pm_area  = _area_m2(df.iloc[ROW_PMFLOW, COL_AREA])
    out["power_module_flow"] = pm_speed * pm_area * 60000.0 / TOTAL_FLOW_LPM
    return out


def main(write=False):
    if not os.path.exists(V3_RESULTS_PATH):
        print(f"✗ V3 결과표 없음: {V3_RESULTS_PATH}")
        print("  → 복원 불가. main.py를 그냥 돌려서 DOE부터 새로 시작하세요.")
        return

    v3 = pd.read_csv(V3_RESULTS_PATH)
    need = set(PARAM_NAMES) | {"weight"}
    if not need <= set(v3.columns):
        print(f"✗ results_v3.csv에 필요한 컬럼이 없음: {sorted(need - set(v3.columns))}")
        return

    rows, missing, broken = [], [], []
    for _, r in v3.iterrows():
        idx = int(r["idx"])
        raw = os.path.join(V3_RESULT_DIR, f"result_{idx:03d}.csv")
        if not os.path.exists(raw):
            missing.append(idx)
            continue
        try:
            vals = _parse_raw(raw)
        except Exception as e:
            broken.append((idx, str(e)[:80]))
            continue

        row = {"idx": len(rows)}                      # V4 기준으로 번호 다시 매김
        row.update({p: float(r[p]) for p in PARAM_NAMES})
        row.update(vals)
        row["weight"] = float(r["weight"])            # SolidWorks 값 — 원본 CSV에 없어서 그대로 가져옴
        # 예측값/오차 컬럼은 비워둠 — 이 점들은 '학습 데이터'이지 '예측 대상'이 아니므로
        for n in MODELED_NAMES:
            row[f"pred_{n}"] = np.nan
            row[f"err_{n}"]  = np.nan
        for p in (1, 2):
            row[f"pred_vel_cv_pass{p}"] = np.nan
            row[f"err_vel_cv_pass{p}"]  = np.nan
        rows.append(row)

    print(f"V3 결과표 {len(v3)}행 중 복원 가능: {len(rows)}점")
    if missing:
        print(f"  · 원본 CSV 없음 {len(missing)}점: {missing[:15]}{' ...' if len(missing) > 15 else ''}")
    if broken:
        print(f"  · 파싱 실패 {len(broken)}점:")
        for i, msg in broken[:5]:
            print(f"      idx {i}: {msg}")

    if not rows:
        print("\n복원할 게 없습니다 — main.py로 DOE부터 새로 시작하세요.")
        return

    df = pd.DataFrame(rows)
    ordered = [c for c in _COLUMNS if c in df.columns]
    extras  = [c for c in df.columns if c not in _COLUMNS]
    df = df[ordered + extras]

    # 복원 검증: 원본 CSV에서 다시 계산한 CV가 V3가 기록해둔 CV와 일치하는지
    #   (일치하면 레인값을 제대로 읽었다는 뜻 — 행 위치나 열 인덱스 착오가 없었음)
    if "vel_cv_pass1" in v3.columns:
        ok_idx = [int(r["idx"]) for _, r in v3.iterrows()
                  if int(r["idx"]) not in missing and
                  int(r["idx"]) not in [b[0] for b in broken]]
        old = v3.set_index("idx").loc[ok_idx, "vel_cv_pass1"].values
        new = df["vel_cv_pass1"].values[:len(old)]
        d = np.abs(old - new)
        print(f"\n검증 — 복원한 레인값으로 다시 계산한 CV vs V3 기록값:")
        print(f"  최대 차이 {d.max():.6f}%p, 평균 {d.mean():.6f}%p")
        if d.max() > 0.01:
            print("  ⚠ 차이가 큽니다 — 행 위치(ROW_LANE1/2)나 열 인덱스가 V3와 다를 수 있음. 확인 필요")
        else:
            print("  ✔ 일치 — 레인값을 올바르게 복원했습니다")

    if not write:
        print(f"\n(확인 모드 — 파일 안 씀. 실제로 만들려면: python seed_from_raw.py --write)")
        print(f"  만들어질 파일: {RESULTS_PATH}  ({len(df)}행)")
        return

    if os.path.exists(RESULTS_PATH):
        print(f"\n✗ 이미 존재함: {RESULTS_PATH}")
        print("  덮어쓰려면 직접 지우고 다시 실행하세요.")
        return

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)
    print(f"\n✔ 생성 완료: {RESULTS_PATH}  ({len(df)}행)")
    print("  이제 main.py를 돌리면 이 데이터를 이어받아 적응샘플링부터 시작합니다.")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
