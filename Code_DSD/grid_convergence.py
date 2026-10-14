"""
V6 격자 민감도 시험 — y(핀 갭 방향) → z(유로 깊이 방향) 순서

⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks/AEDT 사용).
⚠ 결과는 Result/GCI 에 따로 저장되며 DSD/OLHD 결과와 섞이지 않는다.
⚠ 각 레벨이 끝날 때마다 저장하므로, 중간에 끊겨도 다시 실행하면 남은 레벨부터 이어서 한다.
  y 결과가 이미 다 있으면 y 는 건너뛰고 바로 z 를 돌린다. 한 축만 돌리려면 인자를 준다:
      python grid_convergence.py        → y 남은 레벨, 이어서 z 남은 레벨
      python grid_convergence.py z      → z 만

왜 셀 크기를 축별로 바꾸나
  이 모델은 판재+핀이 한 덩어리, 유체(PAO)도 한 덩어리라서 MinElementsOnEdge / MinElementsInGap
  ("물체 사이 틈", "각 물체의 모서리"에 적용) 을 바꿔도 핀·갭 메시가 바뀌지 않았다(실측: 2→3 에서
  요소 2,794,022 → 2,794,030). MLM 레벨을 올리면 x·y·z 를 모두 쪼개 700만 개로 폭증했다.
  그래서 유체 서브리전의 최대 셀 크기를 축별로 바꾼다.

1) y 시험 (DSD 전에 완료) — 가장 얇은 핀(1.5 mm)에 셀 2 / 3 / 4 / 5 / 6개
     y = 0.75 / 0.5 / 0.375 / 0.3 / 0.25 mm,  x·z 는 2.0 mm 고정.  → MESH_REGION_Y = 0.3 (5셀) 채택
     ※ y 시험은 Opening1 역류 허용 상태(DSD 와 같은 설정)로 돌렸다.
2) z 시험 (OLHD 전) — 유로 깊이(8 mm)에 셀 2 / 3 / 4 / 5 / 6개 (y 시험과 같은 셀 수)
     z = 4.0 / 2.667 / 2.0 / 1.6 / 1.333 mm,  y = 0.3(채택값), x = 2.0 mm 고정. 현재 캠페인 값은 4셀(2.0 mm).
     z = 2.0 mm(4셀) 레벨은 y 시험의 y = 0.3 mm 결과와 같은 메시·설계라, y 결과가 있으면 해석 없이
     그 값을 가져다 쓴다 — 단 y 시험과 같은 코드(Opening1 역류 허용)일 때만. 역류 차단이 들어간
     icepak.py 로 돌리면 설정이 달라지므로 재사용하지 않고 해석한다.
     z 를 가늘게 하면 단면 유량의 측정 편향(벽 쪽 굵은 셀에서 속도가 0으로 보간)도 줄어드는지
     함께 본다 — 1차 통과 유로 합계(sum_pass1)가 4 LPM 에 가까워지는지.

고정 조건 (두 시험 공통)
  · 형상: 1차·2차 뱅크 모두 핀 두께 1.5 mm, 핀 24개 (갭 2.02 mm). 나머지 7개 변수는 범위 중앙값.
  · 그 외 메시 설정(MLM 레벨 0, MinGap 0.1 mm, 최소 셀 수 등)은 icepak.py 값 그대로.

판정 (두 시험 공통)
  · 가장 촘촘한 레벨 대비 각 레벨의 차이
      차압·온도편차·유량편차·분기비: 상대 차이 ≤ TOL_PCT
      최고온도: 절대 차이 ≤ TOL_MAXT_K   (절대온도라 % 판정이 무의미)
  · 모든 응답이 통과하는 가장 굵은 레벨을 권장값으로 출력한다.
  · GCI (Celik et al. 2008, 공통비가 일정하지 않을 때의 반복식)는 축마다 세 레벨로 계산한다.
      y: 3 / 4 / 6 셀 (격자 비 1.33, 1.5)
      z: 3 / 4 / 6 셀 (격자 비 1.33, 1.5 — y 와 같음. 현재 캠페인 값 4셀이 GCI 레벨에 들어간다)
  · 총 요소 수와 갭·핀 셀 수는 코드가 기록하지 않는다 — 레벨마다 AEDT 메시 정보에서 직접 적을 것.
"""
import json
import math
import os
import sys
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
FIN_THICK_MM = 1.5                             # 두 뱅크 공통
FIN_COUNT    = 24                              # 두 뱅크 공통
TOL_PCT      = 2.0                             # 상대 차이 허용치 [%] (최고온도 제외)
TOL_MAXT_K   = 0.2                             # 최고온도 절대 차이 허용치 [K]
#   0.2 K 는 V5 대리모델이 설계 간 차이를 구분하던 문턱(약 0.17 K)과 같은 수준.
MESH_X_MM    = 2.0                             # 흐름 방향 (두 시험 공통)

# y 시험: 가장 얇은 핀(1.5 mm)에 셀 2 / 3 / 4 / 5 / 6개
Y_LEVELS     = [0.75, 0.5, 0.375, 0.3, 0.25]   # y 최대 셀 크기 [mm] (성긴 → 촘촘한 순)
Y_GCI_LEVELS = [0.25, 0.375, 0.5]              # GCI 3레벨 (촘촘한 순) — 6 / 4 / 3 셀
Y_TEST_Z_MM  = 2.0                             # y 시험 때 z (당시 캠페인 값)

# z 시험: 유로 깊이(8 mm)에 셀 2 / 3 / 4 / 5 / 6개
Z_CELLS      = [2, 3, 4, 5, 6]
Z_GCI_CELLS  = [6, 4, 3]                       # GCI 3레벨 (촘촘한 순) — 비 1.5, 1.33
Z_TEST_Y_MM  = icepak.MESH_REGION_Y            # y 시험으로 채택한 값 (0.3 mm)
# ═══════════════════════════════════════════════════════

RESP = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow"]
# weight 는 SolidWorks 형상에서 나오므로 격자와 무관 — 비교에서 제외
# z 시험에서 같이 기록하는 참고값 (판정에는 쓰지 않음)
DIAG_Z = ["sum_pass1", "power_module_flow_raw", "T_pass1", "T_outlet"]


def _z_mm(cells):
    return icepak.CHANNEL_DEPTH_MM / cells


AXES = {
    "y": dict(
        levels=Y_LEVELS, gci=Y_GCI_LEVELS, idx_base=900, col="mesh_y_mm",
        results=os.path.join(GCI_DIR, "gci_y_results.csv"),
        summary=os.path.join(GCI_DIR, "gci_y_summary.json"),
        mesh=lambda h: (MESH_X_MM, h, Y_TEST_Z_MM),
        cells=lambda h: FIN_THICK_MM / h, cell_label="핀 1.5mm당 셀",
        resp=RESP, diag=[],
    ),
    "z": dict(
        levels=[_z_mm(n) for n in Z_CELLS], gci=[_z_mm(n) for n in Z_GCI_CELLS], idx_base=910,
        col="mesh_z_mm",
        results=os.path.join(GCI_DIR, "gci_z_results.csv"),
        summary=os.path.join(GCI_DIR, "gci_z_summary.json"),
        mesh=lambda h: (MESH_X_MM, Z_TEST_Y_MM, h),
        cells=lambda h: icepak.CHANNEL_DEPTH_MM / h, cell_label="유로 8mm당 셀",
        resp=RESP, diag=DIAG_Z,
    ),
}


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


def _load(axis):
    a = AXES[axis]
    if os.path.exists(a["results"]):
        return pd.read_csv(a["results"])
    return pd.DataFrame(columns=[a["col"], "minutes"] + a["resp"] + a["diag"])


def _done_levels(axis, df):
    col = AXES[axis]["col"]
    return {round(float(v), 4) for v in df[col]} if len(df) else set()


def _save(axis, h, minutes, results):
    a = AXES[axis]
    df = _load(axis)
    if len(df):
        df = df[(df[a["col"]] - h).abs() > 1e-9]
    row = {a["col"]: h, "minutes": minutes, **{k: results.get(k, np.nan) for k in a["resp"] + a["diag"]}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values(a["col"], ascending=False)
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(a["results"], index=False)


def run_level(app, errors, warnings_, desktop, ipk, params, axis, k, h):
    a = AXES[axis]
    mx, my, mz = a["mesh"](h)
    # icepak.py 의 모듈 상수를 이 프로세스 안에서만 덮어씀 (파일은 바뀌지 않음)
    icepak.MESH_REGION_X, icepak.MESH_REGION_Y, icepak.MESH_REGION_Z = mx, my, mz
    print(f"\n{'='*72}\n[격자 시험 {axis}] {axis} = {h:.4g} mm ({a['cell_label']} {a['cells'](h):.0f}개)"
          f"  (x = {mx}, y = {my:.4g}, z = {mz:.4g} mm)\n{'='*72}")
    idx = a["idx_base"] + k
    t0 = time.time()
    al_mass, al_vol = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, "gci", idx)
    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    results = extract_and_save(f"gci:{axis}{h:.4g}", params, result_path, al_mass, al_vol)
    # 1차 통과 유로 유량 합계 — 입구 4 LPM 에 얼마나 가까운지 (단면 유량 측정 편향 확인용)
    results["sum_pass1"] = results["mean_pass1"] * (params["fin_count_1"] + 1)
    minutes = (time.time() - t0) / 60
    _save(axis, h, minutes, results)
    print(f"[격자 시험 {axis}] {axis} = {h:.4g} mm 완료 ({minutes:.0f}분) "
          f"— AEDT 메시에서 총 요소 수, 갭·핀 셀 수를 기록해 둘 것")
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


def report(axis, params):
    a = AXES[axis]
    col = a["col"]
    df = _load(axis)
    done = _done_levels(axis, df)
    if len(done) < len(a["levels"]):
        print(f"[격자 시험 {axis}] {len(done)}/{len(a['levels'])} 레벨 완료: {sorted(done, reverse=True)}")
        if len(done) < 2:
            return
    df = df.assign(key=df[col].round(4)).set_index("key").sort_index(ascending=False)
    ref_h = df.index.min()
    ref = df.loc[ref_h]
    mx, my, mz = a["mesh"](ref_h)
    fixed = {"y": f"x = {mx}, z = {mz:.4g} mm", "z": f"x = {mx}, y = {my:.4g} mm"}[axis]

    print(f"\n{'='*112}\n[격자 시험 {axis}] 결과 — 기준: 가장 촘촘한 {axis} = {ref_h:.4g} mm  ({fixed})\n{'='*112}")
    print(f"{axis+'(mm)':>7s} {'셀':>3s} {'시간(분)':>8s} " + " ".join(f"{k[:14]:>16s}" for k in a["resp"]) + "  판정")
    verdict = {}
    for h, row in df.iterrows():
        ok = True
        cells = []
        for k in a["resp"]:
            if k == "max_temp":
                d = row[k] - ref[k]
                ok &= abs(d) <= TOL_MAXT_K
                cells.append(f"{row[k]:.3f}({d:+.2f}K)")
            else:
                d = 100 * (row[k] - ref[k]) / ref[k]
                ok &= abs(d) <= TOL_PCT
                cells.append(f"{row[k]:.4g}({d:+.1f}%)")
        verdict[float(h)] = bool(ok)
        print(f"{h:7.4f} {a['cells'](h):3.0f} {row['minutes']:8.0f} " + " ".join(c.rjust(16) for c in cells)
              + f"  {'기준' if h == ref_h else ('통과' if ok else '초과')}")

    if a["diag"]:
        print(f"\n  참고값 (판정 제외) — sum_pass1 은 입구 4 LPM 에 가까울수록 단면 유량 측정 편향이 작다")
        print(f"{axis+'(mm)':>7s} {'셀':>3s} " + " ".join(f"{k[:21]:>22s}" for k in a["diag"]))
        for h, row in df.iterrows():
            print(f"{h:7.4f} {a['cells'](h):3.0f} " + " ".join(f"{row.get(k, np.nan):22.4f}" for k in a["diag"]))

    passing = [h for h in sorted(verdict, reverse=True) if verdict[h]]
    pick = passing[0] if passing else ref_h
    print(f"\n허용치 (상대 {TOL_PCT}%, 최고온도 {TOL_MAXT_K} K) 기준 권장 MESH_REGION_{axis.upper()} = {pick:.4g} mm "
          f"({a['cell_label']} {a['cells'](pick):.0f}개, {fixed})")
    print("  ※ 유량편차(std_pass1/2)는 값 자체가 작아 상대 차이가 크게 보일 수 있다 — 절대 차이도 함께 볼 것")

    gci = {}
    g_keys = [round(v, 4) for v in a["gci"]]
    if all(k in df.index for k in g_keys):
        h3 = tuple(a["gci"])
        print(f"\nGCI ({axis} = " + " / ".join(f"{v:.4g}" for v in h3) + " mm, "
              + " / ".join(f"{a['cells'](v):.0f}" for v in h3) + " 셀)")
        for k in a["resp"]:
            g = gci_three(h3, tuple(df.loc[key, k] for key in g_keys))
            gci[k] = g
            fmt = lambda v, d=2: "N/A" if v != v else f"{v:.{d}f}"
            print(f"    {k:18s} p={fmt(g['p']):>5s}  외삽값={fmt(g['f_ext'], 5):>12s}  "
                  f"GCI_fine={fmt(g['gci_fine']):>6s}%  {g['note']}")

    with open(a["summary"], "w", encoding="utf-8") as f:
        json.dump({"axis": axis, "design": {k: params[k] for k in CANDIDATES},
                   "fixed_mesh": fixed, "levels_mm": a["levels"], "gci_levels_mm": a["gci"],
                   "tol_pct": TOL_PCT, "tol_maxt_k": TOL_MAXT_K,
                   "results": df.reset_index(drop=True).to_dict(orient="records"),
                   "pass": {str(k): v for k, v in verdict.items()},
                   f"recommended_mesh_{axis}_mm": float(pick), "gci": gci},
                  f, ensure_ascii=False, indent=2, default=float)
    print(f"\n요약 저장: {a['summary']}")


def _reuse_y_baseline(h):
    """z = Y_TEST_Z_MM 레벨은 y 시험의 y = Z_TEST_Y_MM 결과와 같은 해석이다(x·y·z 메시, 설계 동일).
    y 결과가 있고 icepak.py 가 y 시험 당시 설정(역류 허용 — T_pass1 측정면이 없는 버전)이면
    그 행을 z 결과로 복사하고 True. 참고값(DIAG_Z)은 y 결과에 없어 빈칸으로 남는다."""
    if abs(h - Y_TEST_Z_MM) > 1e-9:
        return False
    if hasattr(icepak, "T_PASS1_INSET_MM"):
        print(f"[격자 시험 z] z = {h:.4g} mm — icepak.py 가 역류 차단 버전이라 y 결과를 재사용하지 않고 해석함")
        return False
    y = _load("y")
    if not len(y):
        return False
    hit = y[(y[AXES["y"]["col"]] - Z_TEST_Y_MM).abs() < 1e-9]
    if not len(hit):
        return False
    row = hit.iloc[0]
    _save("z", h, float(row["minutes"]), {k: row[k] for k in RESP})
    print(f"[격자 시험 z] z = {h:.4g} mm — y 시험의 y = {Z_TEST_Y_MM:.4g} mm 결과와 같은 해석이라 재사용 (해석 생략)")
    return True


def main(axes=("y", "z")):
    params = test_design()
    sw = aedt = None
    for axis in axes:
        a = AXES[axis]
        done = _done_levels(axis, _load(axis))
        todo = [(k, h) for k, h in enumerate(a["levels"]) if round(h, 4) not in done]
        if axis == "z":
            todo = [(k, h) for k, h in todo if not _reuse_y_baseline(h)]
        if not todo:
            print(f"[격자 시험 {axis}] 모든 레벨 완료 — 건너뜀")
            continue
        print(f"[격자 시험 {axis}] 남은 레벨: {[round(h, 4) for _, h in todo]}  (완료: {sorted(done, reverse=True)})")
        if sw is None:
            sw = connect_sw()
            aedt = list(connect_aedt())
        app, errors, warnings_ = sw
        desktop, ipk = aedt
        for k, h in todo:
            ipk = run_level(app, errors, warnings_, desktop, ipk, params, axis, k, h)
        aedt[1] = ipk
    for axis in axes:
        report(axis, params)


if __name__ == "__main__":
    args = [s.lower() for s in sys.argv[1:]]
    bad = [s for s in args if s not in AXES]
    if bad:
        raise SystemExit(f"알 수 없는 축 {bad} — y, z 중에서 고를 것 (예: python grid_convergence.py z)")
    main(tuple(args) if args else ("y", "z"))
