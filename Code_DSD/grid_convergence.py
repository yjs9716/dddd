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
     z = 4.0 / 2.667 / 2.0 / 1.6 / 1.333 mm,  y = 0.3(채택값), x = 2.0 mm 고정.
     → MESH_REGION_Z = 1.6 (5셀) 채택: 6셀 대비 차압 −1.6%, 최고온도 −0.04 K, 분기비 −0.2%.
       4셀(2.0 mm, DSD 때 값)은 차압 −3.8%로 초과.
     ※ z 시험은 내부망 기존 icepak.py(역류 허용·발열 9개·분기 입구 z 2.0 mm 고정)로 돌렸다.
     ※ 4셀 행은 처음에 y 시험의 y = 0.3 mm 결과를 복사해 넣었는데, y 시험 뒤에 분기 입구 국소 메시와
       분기 유량 측정면 위치가 바뀌어 같은 해석이 아니었다(분기비 0.366 vs 다른 레벨 0.47~0.48).
       해석 시간(minutes_icepak)이 빈 z 행은 그 복사본으로 보고 다시 해석한다 — 기존 icepak.py 로
       `python grid_convergence.py z` 를 돌리면 4셀만 돈다(아래 "해석 조건" 참고).
     z 를 가늘게 하면 단면 유량의 측정 편향(벽 쪽 굵은 셀에서 속도가 0으로 보간)도 줄어드는지
     함께 본다 — 1차 통과 유로 합계(sum_pass1): 2셀 1.88 → 6셀 3.22 LPM (입구 4 LPM).

고정 조건 (두 시험 공통)
  · 형상: 1차·2차 뱅크 모두 핀 두께 1.5 mm, 핀 24개 (갭 2.02 mm). 나머지 7개 변수는 범위 중앙값.
  · 그 외 메시 설정(MLM 레벨 0, MinGap 0.1 mm, 최소 셀 수 등)은 icepak.py 값 그대로.

판정 (두 시험 공통)
  · 가장 촘촘한 레벨 대비 각 레벨의 차이 — JUDGE 의 세 응답만 판정한다
      차압·분기비: 상대 차이 ≤ TOL_PCT
      최고온도: 절대 차이 ≤ TOL_MAXT_K   (절대온도라 % 판정이 무의미)
  · 온도편차·유로 유량편차(std_pass1/2)는 기록만 한다. 값이 작고(유량편차 0.002~0.007 LPM,
    온도편차 약 0.2 K) 격자에 따라 오르내리기만 해서 상대 차이 판정이 성립하지 않는다.
    대신 격자 간 차이를 설계 간 변동 범위(V6 예비 110점)와 비교한다 — 5셀 vs 6셀 차이가
    y·z 모두 범위의 3% 이하(온도편차 3.1% / 1.4%, 유량편차 0.5% 이하).
  · 세 응답이 모두 통과하는 가장 굵은 레벨을 권장값으로 출력한다.

해석 조건 (setup 열)
  · 결과 행마다 icepak.py 의 해석 조건(출구 역류 차단 여부, 발열채널 수)을 남긴다. 한 시험 안에서
    조건이 섞이면 레벨끼리 비교가 안 되므로, 기존 행과 지금 icepak.py 의 조건이 다르면 해석하지
    않고 멈춘다. 이 열을 넣기 전에 돌린 행(빈칸)은 LEGACY_SETUP 으로 본다.
  · GCI (Celik et al. 2008, 공통비가 일정하지 않을 때의 반복식)는 축마다 세 레벨로 계산한다.
      y: 3 / 4 / 6 셀 (격자 비 1.33, 1.5)
      z: 3 / 4 / 6 셀 (격자 비 1.33, 1.5 — y 와 같음. 현재 캠페인 값 4셀이 GCI 레벨에 들어간다)
  · 레벨마다 시간과 총 요소 수를 결과 파일에 기록한다.
      minutes        : 레벨 전체 (SolidWorks 갱신·STEP 내보내기 포함)
      minutes_icepak : Icepak 부분만 (형상 불러오기·메싱·해석·Fields Summary 내보내기)
      elements       : 총 요소 수 — AEDT 메시 통계 파일, 안 되면 메시지 창에서 읽는다. 둘 다 실패하면
                       빈칸(해석은 계속)이니 그 레벨만 AEDT 메시 정보에서 직접 적을 것.
                       첫 레벨에서 출력된 값이 AEDT 화면의 요소 수와 같은지 한 번 확인할 것.
"""
import json
import math
import os
import re
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
# 판정에 쓰는 응답 (나머지 RESP 는 기록만 — 위 "판정" 참고)
JUDGE = ["pressure_drop", "max_temp", "power_module_flow"]
# z 시험에서 같이 기록하는 참고값 (판정에는 쓰지 않음)
DIAG_Z = ["sum_pass1", "power_module_flow_raw", "T_pass1", "T_outlet"]


# 레벨마다 같이 기록하는 실행 정보 (판정에는 쓰지 않음)
INFO = ["minutes_icepak", "elements"]

# setup 열이 빈 행 = 이 열을 넣기 전에 돌린 행 (y·z 시험 모두 내부망 기존 icepak.py: 역류 허용·발열 9개)
LEGACY_SETUP = "역류허용·발열9개"


def _setup():
    """지금 import 한 icepak.py 의 해석 조건. T_PASS1_INSET_MM 은 역류 차단과 함께 들어간 상수다."""
    nrf = "역류차단" if hasattr(icepak, "T_PASS1_INSET_MM") else "역류허용"
    return f"{nrf}·발열{getattr(icepak, 'N_SOURCE', '?')}개"


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
    return pd.DataFrame(columns=[a["col"], "minutes", "setup"] + INFO + a["resp"] + a["diag"])


def _done_levels(axis, df):
    """끝난 레벨. z 에서 해석 시간이 빈 행은 y 결과를 복사해 넣었던 4셀 행이라 끝난 것으로 보지 않는다."""
    col = AXES[axis]["col"]
    if not len(df):
        return set()
    if axis == "z" and "minutes_icepak" in df:
        df = df[df["minutes_icepak"].notna()]
    return {round(float(v), 4) for v in df[col]}


def _check_setup(axis, df):
    """기존 행과 지금 icepak.py 의 해석 조건이 같은지. 다르면 해석하지 않고 멈춘다."""
    if not len(df):
        return
    old = set(df["setup"].fillna(LEGACY_SETUP)) if "setup" in df else {LEGACY_SETUP}
    now = _setup()
    if old != {now}:
        raise SystemExit(
            f"[격자 시험 {axis}] 기존 레벨은 {sorted(old)} 조건으로 돌렸는데 지금 icepak.py 는 {now} 이다.\n"
            f"  섞이면 레벨끼리 비교가 안 된다 — 기존 레벨과 같은 icepak.py 로 돌리거나,\n"
            f"  새 조건으로 처음부터 하려면 {AXES[axis]['results']} 를 지우고 다시 돌릴 것.")


def _save(axis, h, minutes, results, info=None):
    a = AXES[axis]
    df = _load(axis)
    if len(df):
        df = df[(df[a["col"]] - h).abs() > 1e-9]
    info = info or {}
    row = {a["col"]: h, "minutes": minutes, "setup": _setup(), **{k: info.get(k, np.nan) for k in INFO},
           **{k: results.get(k, np.nan) for k in a["resp"] + a["diag"]}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values(a["col"], ascending=False)
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(a["results"], index=False)


_ELEMENT_PATTERNS = [
    r"(?i)total\s*(?:number\s*of\s*)?(?:elements|cells)\D{0,20}?([\d,]{4,})",
    r"(?i)(?:number\s*of\s*)?(?:elements|cells)\s*[:=]\s*([\d,]{4,})",
    r"(?i)([\d,]{4,})\s*(?:elements|cells)",
]


def _parse_elements(text):
    """글에서 요소 수로 보이는 숫자를 찾는다 (패턴 순서대로, 각 패턴의 마지막 일치값)."""
    for pat in _ELEMENT_PATTERNS:
        hits = [int(m.replace(",", "")) for m in re.findall(pat, text)]
        hits = [n for n in hits if n >= 1000]
        if hits:
            return hits[-1]
    return None


def _mesh_elements(ipk, idx):
    """총 요소 수 [개] 와 출처. AEDT 버전마다 되는 방법이 달라 순서대로 시도하고, 다 실패하면 nan."""
    try:
        path = os.path.join(GCI_DIR, f"meshstats_gci_{idx:03d}.txt")
        ipk.odesign.ExportMeshStats("Setup1", "", path)
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as f:
                n = _parse_elements(f.read())
            if n:
                return n, f"메시 통계 파일 {os.path.basename(path)}"
    except Exception as e:
        print(f"  (메시 통계 파일 내보내기 실패: {e})")
    try:
        msgs = ipk.odesktop.GetMessages(ipk.project_name, ipk.design_name, 0)
        n = _parse_elements("\n".join(str(m) for m in msgs))
        if n:
            return n, "AEDT 메시지 창"
    except Exception as e:
        print(f"  (AEDT 메시지 읽기 실패: {e})")
    return np.nan, ""


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
    t1 = time.time()
    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    t2 = time.time()
    results = extract_and_save(f"gci:{axis}{h:.4g}", params, result_path, al_mass, al_vol)
    # 1차 통과 유로 유량 합계 — 입구 4 LPM 에 얼마나 가까운지 (단면 유량 측정 편향 확인용)
    results["sum_pass1"] = results["mean_pass1"] * (params["fin_count_1"] + 1)
    elements, source = _mesh_elements(ipk, idx)
    minutes = (time.time() - t0) / 60
    info = {"minutes_icepak": (t2 - t1) / 60, "elements": elements}
    _save(axis, h, minutes, results, info)
    el_txt = f"{elements:,.0f}개 ({source})" if elements == elements else "읽기 실패 — AEDT 메시 정보에서 직접 적을 것"
    print(f"[격자 시험 {axis}] {axis} = {h:.4g} mm 완료 — 전체 {minutes:.0f}분 "
          f"(Icepak {info['minutes_icepak']:.0f}분), 총 요소 수 {el_txt}")
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
    print(f"판정: {', '.join(JUDGE)} (차압·분기비 ±{TOL_PCT}%, 최고온도 ±{TOL_MAXT_K} K) — "
          f"나머지는 기록만 (괄호 안 차이에 * 없음)")
    print(f"{axis+'(mm)':>7s} {'셀':>3s} {'전체(분)':>8s} {'해석(분)':>8s} {'요소 수':>11s} "
          + " ".join(f"{k[:14]:>16s}" for k in a["resp"]) + "  판정")
    verdict = {}
    for h, row in df.iterrows():
        ok = True
        cells = []
        for k in a["resp"]:
            mark = "*" if k in JUDGE else ""
            if k == "max_temp":
                d = row[k] - ref[k]
                ok &= (k not in JUDGE) or abs(d) <= TOL_MAXT_K
                cells.append(f"{row[k]:.3f}({d:+.2f}K{mark})")
            else:
                d = 100 * (row[k] - ref[k]) / ref[k]
                ok &= (k not in JUDGE) or abs(d) <= TOL_PCT
                cells.append(f"{row[k]:.4g}({d:+.1f}%{mark})")
        verdict[float(h)] = bool(ok)
        n_el = row.get("elements", np.nan)
        el = f"{n_el:,.0f}" if n_el == n_el else "-"
        print(f"{h:7.4f} {a['cells'](h):3.0f} {row['minutes']:8.0f} {row.get('minutes_icepak', np.nan):8.0f} {el:>11s} "
              + " ".join(c.rjust(16) for c in cells)
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
    setups = set(df["setup"].fillna(LEGACY_SETUP)) if "setup" in df else {LEGACY_SETUP}
    print(f"  해석 조건: {', '.join(sorted(setups))}"
          + ("  ⚠ 조건이 섞여 있음 — 비교 불가" if len(setups) > 1 else ""))

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
                   "tol_pct": TOL_PCT, "tol_maxt_k": TOL_MAXT_K, "judged": JUDGE,
                   "results": df.reset_index(drop=True).to_dict(orient="records"),
                   "pass": {str(k): v for k, v in verdict.items()},
                   f"recommended_mesh_{axis}_mm": float(pick), "gci": gci},
                  f, ensure_ascii=False, indent=2, default=float)
    print(f"\n요약 저장: {a['summary']}")


def main(axes=("y", "z")):
    params = test_design()
    sw = aedt = None
    for axis in axes:
        a = AXES[axis]
        existing = _load(axis)
        done = _done_levels(axis, existing)
        todo = [(k, h) for k, h in enumerate(a["levels"]) if round(h, 4) not in done]
        if not todo:
            print(f"[격자 시험 {axis}] 모든 레벨 완료 — 건너뜀")
            continue
        _check_setup(axis, existing)
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
