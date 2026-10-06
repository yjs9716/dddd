"""
V6 격자 민감도 시험 — 핀 갭 방향(y) 최대 셀 크기 0.75 / 0.5 / 0.375 / 0.3 / 0.25 mm

⚠ DSD(main.py)를 시작하기 전에 실행한다. 여기서 정한 y 크기를 icepak.py 의 MESH_REGION_Y 에
  고정하고, x·z 는 시험과 같은 값(MESH_X_MM, MESH_Z_MM)으로 맞춘 뒤 캠페인 전체에 쓴다.
⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks/AEDT 사용).
⚠ 결과는 Result/GCI 에 따로 저장되며 DSD/OLHD 결과와 섞이지 않는다.

왜 y 크기인가
  이 모델은 판재+핀이 한 덩어리, 유체(PAO)도 한 덩어리라서 MinElementsOnEdge / MinElementsInGap
  ("물체 사이 틈", "각 물체의 모서리"에 적용) 을 바꿔도 핀·갭 메시가 바뀌지 않았다(실측: 2→3 에서
  요소 2,794,022 → 2,794,030). MLM 레벨을 올리면 x·y·z 를 모두 쪼개 700만 개로 폭증했다.
  그래서 갭·핀을 가로지르는 y 방향 최대 셀 크기만 줄이고, 흐름 방향 x 와 깊이 방향 z 는
  2.0 mm 로 키워 총 셀 수를 억제한다.

고정 조건
  · 형상: 1차·2차 뱅크 모두 핀 두께 1.5 mm, 핀 24개 (갭 2.02 mm). 나머지 7개 변수는 범위 중앙값.
  · 유체 서브리전 최대 셀: x = MESH_X_MM, z = MESH_Z_MM (2.0 mm), y 만 레벨별로 바꿈.
  · 그 외 메시 설정(MLM 레벨 0, MinGap 0.1 mm, 최소 셀 수 등)은 icepak.py 값 그대로.

판정
  · 가장 촘촘한 레벨(0.25 mm) 대비 각 레벨의 차이
      차압·온도편차·유량편차·분기비: 상대 차이 ≤ TOL_PCT
      최고온도: 절대 차이 ≤ TOL_MAXT_K   (절대온도라 % 판정이 무의미)
  · 모든 응답이 통과하는 가장 큰 y 를 권장값으로 출력한다.
  · GCI (Celik et al. 2008, 공통비가 일정하지 않을 때의 반복식)는 GCI_LEVELS 세 레벨로 계산한다.
    공통비가 1.3 이상이 되도록 0.25 / 0.375 / 0.5 를 기본으로 쓴다 (0.3↔0.25 는 비율 1.2 로 너무 가까움).
  · 각 레벨이 끝날 때마다 저장하므로, 중간에 끊겨도 다시 실행하면 남은 레벨부터 이어서 한다.
  · 총 요소 수와 갭·핀 셀 수는 코드가 기록하지 않는다 — 레벨마다 AEDT 메시 정보에서 직접 적을 것.
"""
import json
import math
import os
import time

import numpy as np
import pandas as pd

import icepak
from Solidworks import connect_sw, update_sw, export_step
from icepak import connect_aedt, run_icepak
from result_parser import extract_and_save
from params import CANDIDATES, N_CAND_DIM, decode, to_dict
from fins import all_banks_feasible, describe_bank, BANKS
from paths import GCI_DIR

# ══════════════ 시험 설정 — 실행 전에 확정 ══════════════
Y_LEVELS     = [0.75, 0.5, 0.375, 0.3, 0.25]   # y 최대 셀 크기 [mm] (성긴 → 촘촘한 순)
GCI_LEVELS   = [0.25, 0.375, 0.5]              # GCI 계산용 3레벨 (촘촘한 순, 공통비 ≥ 1.3)
MESH_X_MM    = 2.0                             # 흐름 방향 (전 레벨 공통)
MESH_Z_MM    = 2.0                             # 깊이 방향 (전 레벨 공통)
FIN_THICK_MM = 1.5                             # 두 뱅크 공통
FIN_COUNT    = 24                              # 두 뱅크 공통
TOL_PCT      = 2.0                             # 상대 차이 허용치 [%] (최고온도 제외)
TOL_MAXT_K   = 0.2                             # 최고온도 절대 차이 허용치 [K]
#   0.2 K 는 V5 대리모델이 설계 간 차이를 구분하던 문턱(약 0.17 K)과 같은 수준.
# ═══════════════════════════════════════════════════════

GCI_IDX_BASE = 900                             # 결과 파일 번호 900~904 (캠페인 idx와 겹치지 않게)
RESP = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow"]
# weight 는 SolidWorks 형상에서 나오므로 격자와 무관 — 비교에서 제외

RESULTS_PATH = os.path.join(GCI_DIR, "gci_y_results.csv")
SUMMARY_PATH = os.path.join(GCI_DIR, "gci_y_summary.json")


def test_design():
    """두 뱅크 모두 핀 1.5 mm × 24개, 나머지 변수는 범위 중앙값."""
    p = to_dict(decode(np.full(N_CAND_DIM, 0.5)))
    for b in BANKS:
        p[f"fin_thick_{b}"] = FIN_THICK_MM
        p[f"fin_count_{b}"] = FIN_COUNT
    if not all_banks_feasible(p):
        raise RuntimeError("시험 설계가 갭 제약을 위반함 — FIN_THICK_MM / FIN_COUNT / fins.MIN_GAP_MM 확인")
    print("[격자 시험] 시험 설계")
    for n in CANDIDATES:
        print(f"    {n:20s} = {p[n]}")
    for b in BANKS:
        print(f"    {describe_bank(p, b)}")
    return p


def _load():
    if os.path.exists(RESULTS_PATH):
        return pd.read_csv(RESULTS_PATH)
    return pd.DataFrame(columns=["mesh_y_mm", "minutes"] + RESP)


def _done_levels(df):
    return {round(float(v), 4) for v in df["mesh_y_mm"]} if len(df) else set()


def _save(mesh_y, minutes, results):
    df = _load()
    if len(df):
        df = df[(df["mesh_y_mm"] - mesh_y).abs() > 1e-9]
    row = {"mesh_y_mm": mesh_y, "minutes": minutes, **{k: results[k] for k in RESP}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("mesh_y_mm", ascending=False)
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


def run_level(app, errors, warnings_, desktop, ipk, params, k, mesh_y):
    # icepak.py 의 모듈 상수를 이 프로세스 안에서만 덮어씀 (파일은 바뀌지 않음)
    icepak.MESH_REGION_X = MESH_X_MM
    icepak.MESH_REGION_Y = mesh_y
    icepak.MESH_REGION_Z = MESH_Z_MM
    print(f"\n{'='*72}\n[격자 시험] y = {mesh_y} mm  (x = {MESH_X_MM}, z = {MESH_Z_MM} mm)\n{'='*72}")
    idx = GCI_IDX_BASE + k
    t0 = time.time()
    al_mass, al_vol = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, "gci", idx)
    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    results = extract_and_save(f"gci:y{mesh_y}", params, result_path, al_mass, al_vol)
    minutes = (time.time() - t0) / 60
    _save(mesh_y, minutes, results)
    print(f"[격자 시험] y = {mesh_y} mm 완료 ({minutes:.0f}분) — AEDT 메시에서 총 요소 수, 갭·핀 셀 수를 기록해 둘 것")
    return ipk


def gci_three(h, f):
    """Celik et al. (2008) — 세 격자 (h1<h2<h3, f1=가장 촘촘). 공통비가 다를 때 p 를 반복으로 구한다."""
    (h1, h2, h3), (f1, f2, f3) = h, f
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    if abs(e21) < 1e-14 or abs(e32) < 1e-14:
        return dict(p=np.nan, f_ext=f1, gci_fine=0.0, note="차이 0 — 사실상 수렴")
    s = np.sign(e32 / e21)
    if s < 0:
        return dict(p=np.nan, f_ext=np.nan, gci_fine=np.nan, note="진동수렴 — p 산출 불가")
    p = abs(math.log(abs(e32 / e21))) / math.log(r21)
    for _ in range(200):
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-8:
            break
        p = p_new
    f_ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
    gci_fine = 100 * 1.25 * abs(e21 / f1) / (r21 ** p - 1)
    return dict(p=p, f_ext=f_ext, gci_fine=gci_fine, note="")


def report(params):
    df = _load()
    done = _done_levels(df)
    if len(done) < len(Y_LEVELS):
        print(f"[격자 시험] {len(done)}/{len(Y_LEVELS)} 레벨 완료: {sorted(done, reverse=True)}")
        if len(done) < 2:
            return
    df = df.assign(key=df["mesh_y_mm"].round(4)).set_index("key").sort_index(ascending=False)
    ref_y = df.index.min()
    ref = df.loc[ref_y]

    print(f"\n{'='*104}\n[격자 시험] 결과 — 기준: 가장 촘촘한 y = {ref_y} mm  (x = {MESH_X_MM}, z = {MESH_Z_MM} mm)\n{'='*104}")
    print(f"{'y(mm)':>6s} {'시간(분)':>8s} " + " ".join(f"{k[:14]:>16s}" for k in RESP) + "  판정")
    verdict = {}
    for y, row in df.iterrows():
        ok = True
        cells = []
        for k in RESP:
            if k == "max_temp":
                d = row[k] - ref[k]
                ok &= abs(d) <= TOL_MAXT_K
                cells.append(f"{row[k]:.3f}({d:+.2f}K)")
            else:
                d = 100 * (row[k] - ref[k]) / ref[k]
                ok &= abs(d) <= TOL_PCT
                cells.append(f"{row[k]:.4g}({d:+.1f}%)")
        verdict[float(y)] = bool(ok)
        print(f"{y:6.3f} {row['minutes']:8.0f} " + " ".join(c.rjust(16) for c in cells)
              + f"  {'기준' if y == ref_y else ('통과' if ok else '초과')}")

    passing = [y for y in sorted(verdict, reverse=True) if verdict[y]]
    pick = passing[0] if passing else ref_y
    print(f"\n허용치 (상대 {TOL_PCT}%, 최고온도 {TOL_MAXT_K} K) 기준 권장 MESH_REGION_Y = {pick} mm "
          f"(x = {MESH_X_MM}, z = {MESH_Z_MM} mm)")
    print("  ※ 유량편차(std_pass1/2)는 값 자체가 작아 상대 차이가 크게 보일 수 있다 — 절대 차이도 함께 볼 것")

    gci = {}
    g_keys = [round(v, 4) for v in GCI_LEVELS]
    if all(k in df.index for k in g_keys):
        h = tuple(GCI_LEVELS)
        print(f"\nGCI (y = {h[0]} / {h[1]} / {h[2]} mm)")
        for k in RESP:
            g = gci_three(h, tuple(df.loc[key, k] for key in g_keys))
            gci[k] = g
            fmt = lambda v, d=2: "N/A" if v != v else f"{v:.{d}f}"
            print(f"    {k:18s} p={fmt(g['p']):>5s}  외삽값={fmt(g['f_ext'], 5):>12s}  "
                  f"GCI_fine={fmt(g['gci_fine']):>6s}%  {g['note']}")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump({"design": {k: params[k] for k in CANDIDATES},
                   "mesh_x_mm": MESH_X_MM, "mesh_z_mm": MESH_Z_MM, "y_levels": Y_LEVELS,
                   "tol_pct": TOL_PCT, "tol_maxt_k": TOL_MAXT_K,
                   "results": df.reset_index(drop=True).to_dict(orient="records"),
                   "pass": {str(k): v for k, v in verdict.items()},
                   "recommended_mesh_y_mm": float(pick), "gci": gci},
                  f, ensure_ascii=False, indent=2, default=float)
    print(f"\n요약 저장: {SUMMARY_PATH}")


def main():
    params = test_design()
    done = _done_levels(_load())
    todo = [(k, y) for k, y in enumerate(Y_LEVELS) if round(y, 4) not in done]
    if todo:
        print(f"[격자 시험] 남은 레벨: {[y for _, y in todo]}  (완료: {sorted(done, reverse=True)})")
        app, errors, warnings_ = connect_sw()
        desktop, ipk = connect_aedt()
        for k, y in todo:
            ipk = run_level(app, errors, warnings_, desktop, ipk, params, k, y)
    report(params)


if __name__ == "__main__":
    main()
