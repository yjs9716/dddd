"""
V6 격자 민감도 시험 — MIN_ELEMENTS_ON_EDGE (모서리당 최소 셀 수) 2 / 3 / 4 / 5 / 6

⚠ DSD(main.py)를 시작하기 전에 실행한다. 여기서 정한 값을 icepak.py 에 고정하고 캠페인 전체에 쓴다.
⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks/AEDT 사용).
⚠ 결과는 Result/GCI 에 따로 저장되며 DSD/OLHD 결과와 섞이지 않는다.

무엇을 하는가
  핀 갭이 가장 좁은 설계 하나를 고정하고, 메시 설정 중 "모서리당 최소 셀 수"
  (MinElementsOnEdge)만 2 → 6 으로 바꿔 같은 설계를 5번 해석한다.
  유로 폭(갭)을 가로지르는 PAO 모서리가 이 설정을 따라 N셀로 나뉘면, 갭 안 셀 수가
  N개가 된다는 가정이다 — 레벨마다 AEDT 메시에서 실제 갭 셀 수를 확인해 기록할 것.

고정 조건
  · 형상: 1차·2차 뱅크 모두 핀 두께 1.5 mm, 핀 24개 (갭 2.02 mm). 나머지 7개 변수는 범위 중앙값.
  · 최대 셀 크기: 유체 서브리전 x/y/z = 1.0 mm (아래 MESH_SIZE_MM) — icepak.py 값과 무관하게 덮어씀.
  · 적용 범위: APPLY_TO_GLOBAL 이 False 면 유체 서브리전(MeshRegion1)만 바꾸고 글로벌은 기본값(2).
               True 면 글로벌 메시도 같은 값으로 바꾼다. (글로벌은 판재·외부 공간 전체 모서리에 걸려
               셀 수가 크게 늘 수 있음)

판정
  · 가장 촘촘한 레벨(6) 대비 각 레벨의 차이를 계산한다.
      차압·온도편차·유량편차·분기비: 상대 차이 ≤ TOL_PCT
      최고온도: 절대 차이 ≤ TOL_MAXT_K   (절대온도라 % 판정이 무의미)
  · 모든 응답이 통과하는 가장 작은 N을 권장값으로 출력한다.
  · 촘촘한 3레벨(4, 5, 6)로 GCI (Celik et al. 2008, 공통비가 일정하지 않은 경우의 반복식)도 계산한다.
    대표 격자 크기는 h = 갭 / N (N셀로 나뉜다는 가정).
  · 각 레벨이 끝날 때마다 저장하므로, 중간에 끊겨도 다시 실행하면 남은 레벨부터 이어서 한다.
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
from fins import all_banks_feasible, describe_bank, bank_gap, BANKS
from paths import GCI_DIR

# ══════════════ 시험 설정 — 실행 전에 확정 ══════════════
EDGE_LEVELS     = [2, 3, 4, 5, 6]       # MinElementsOnEdge 값 (작은 순)
MESH_SIZE_MM    = 1.0                   # 유체 서브리전 최대 셀 크기 x/y/z [mm] (전 레벨 공통)
APPLY_TO_GLOBAL = False                 # True 면 글로벌 메시의 MinElementsOnEdge 도 같이 바꿈
FIN_THICK_MM    = 1.5                   # 두 뱅크 공통
FIN_COUNT       = 24                    # 두 뱅크 공통
TOL_PCT         = 2.0                   # 상대 차이 허용치 [%] (최고온도 제외)
TOL_MAXT_K      = 0.2                   # 최고온도 절대 차이 허용치 [K]
#   0.2 K 는 V5 대리모델이 설계 간 차이를 구분하던 문턱(약 0.17 K)과 같은 수준.
# ═══════════════════════════════════════════════════════

GCI_IDX_BASE = 900                      # 결과 파일 번호 (캠페인 idx와 겹치지 않게)
RESP = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow"]
# weight 는 SolidWorks 형상에서 나오므로 격자와 무관 — 비교에서 제외

RESULTS_PATH = os.path.join(GCI_DIR, "gci_edge_results.csv")
SUMMARY_PATH = os.path.join(GCI_DIR, "gci_edge_summary.json")


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
    return pd.DataFrame(columns=["edge_n", "minutes"] + RESP)


def _save(edge_n, minutes, results):
    df = _load()
    df = df[df["edge_n"] != edge_n]
    row = {"edge_n": edge_n, "minutes": minutes, **{k: results[k] for k in RESP}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("edge_n")
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


def run_level(app, errors, warnings_, desktop, ipk, params, edge_n):
    # icepak.py 의 모듈 상수를 이 프로세스 안에서만 덮어씀 (파일은 바뀌지 않음)
    icepak.MESH_REGION_X = icepak.MESH_REGION_Y = icepak.MESH_REGION_Z = MESH_SIZE_MM
    icepak.MIN_ELEMENTS_ON_EDGE = edge_n
    if APPLY_TO_GLOBAL:
        icepak.GLOBAL_MIN_ELEMENTS_ON_EDGE = edge_n
    print(f"\n{'='*72}\n[격자 시험] MinElementsOnEdge = {edge_n} "
          f"(서브리전{' + 글로벌' if APPLY_TO_GLOBAL else ''}), 최대 셀 {MESH_SIZE_MM} mm\n{'='*72}")
    idx = GCI_IDX_BASE + edge_n
    t0 = time.time()
    al_mass, al_vol = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, "gci", idx)
    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    results = extract_and_save(f"gci:edge{edge_n}", params, result_path, al_mass, al_vol)
    minutes = (time.time() - t0) / 60
    _save(edge_n, minutes, results)
    print(f"[격자 시험] edge={edge_n} 완료 ({minutes:.0f}분) — AEDT 메시에서 갭 셀 수와 총 셀 수를 기록해 둘 것")
    return ipk


def gci_three(h, f):
    """Celik et al. (2008) — 세 격자 (h1<h2<h3, f1=가장 촘촘). 공통비가 다를 때 p 를 반복으로 구한다.
    반환: p, 외삽값, GCI_fine[%], note"""
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
    done = sorted(df["edge_n"].astype(int))
    if len(done) < len(EDGE_LEVELS):
        print(f"[격자 시험] {len(done)}/{len(EDGE_LEVELS)} 레벨 완료: {done}")
        if len(done) < 2:
            return
    df = df.set_index("edge_n").sort_index()
    ref_n = df.index.max()
    ref = df.loc[ref_n]
    gap = bank_gap(params, 1)

    print(f"\n{'='*100}\n[격자 시험] 결과 — 기준: 가장 촘촘한 edge={ref_n}\n{'='*100}")
    head = f"{'edge N':>6s} {'시간(분)':>8s} " + " ".join(f"{k[:12]:>12s}" for k in RESP) + "  판정"
    print(head)
    verdict = {}
    for n, row in df.iterrows():
        ok = True
        cells = []
        for k in RESP:
            if k == "max_temp":
                d = row[k] - ref[k]
                ok &= abs(d) <= TOL_MAXT_K
                cells.append(f"{row[k]:7.3f}({d:+.2f}K)")
            else:
                d = 100 * (row[k] - ref[k]) / ref[k]
                ok &= abs(d) <= TOL_PCT
                cells.append(f"{row[k]:.4g}({d:+.1f}%)".rjust(12))
        verdict[int(n)] = bool(ok)
        print(f"{int(n):6d} {row['minutes']:8.0f} " + " ".join(c.rjust(12) for c in cells)
              + f"  {'통과' if ok or n == ref_n else '초과'}")

    passing = [n for n in sorted(verdict) if verdict[n]]
    pick = passing[0] if passing else ref_n
    print(f"\n허용치 (상대 {TOL_PCT}%, 최고온도 {TOL_MAXT_K} K) 기준 권장 MIN_ELEMENTS_ON_EDGE = {pick}")
    print("  ※ 유량편차(std_pass1/2)는 값 자체가 작아 상대 차이가 크게 보일 수 있다 — 절대 차이도 함께 볼 것")

    gci = {}
    top3 = sorted(df.index)[-3:]
    if len(top3) == 3:
        n1, n2, n3 = top3[2], top3[1], top3[0]          # 촘촘한 순
        h = (gap / n1, gap / n2, gap / n3)
        print(f"\nGCI (edge {n1}/{n2}/{n3}, h = 갭/N = {h[0]:.3f}/{h[1]:.3f}/{h[2]:.3f} mm)")
        for k in RESP:
            g = gci_three(h, (df.loc[n1, k], df.loc[n2, k], df.loc[n3, k]))
            gci[k] = g
            fmt = lambda v, d=2: "N/A" if v != v else f"{v:.{d}f}"
            print(f"    {k:18s} p={fmt(g['p']):>5s}  외삽값={fmt(g['f_ext'], 5):>12s}  "
                  f"GCI_fine={fmt(g['gci_fine']):>6s}%  {g['note']}")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump({"design": {k: params[k] for k in CANDIDATES}, "gap_mm": gap,
                   "mesh_size_mm": MESH_SIZE_MM, "apply_to_global": APPLY_TO_GLOBAL,
                   "tol_pct": TOL_PCT, "tol_maxt_k": TOL_MAXT_K,
                   "results": df.reset_index().to_dict(orient="records"),
                   "pass": verdict, "recommended_edge_n": int(pick), "gci": gci},
                  f, ensure_ascii=False, indent=2, default=float)
    print(f"\n요약 저장: {SUMMARY_PATH}")


def main():
    params = test_design()
    df = _load()
    done = set(df["edge_n"].astype(int)) if len(df) else set()
    todo = [n for n in EDGE_LEVELS if n not in done]
    if todo:
        print(f"[격자 시험] 남은 레벨: {todo}  (완료: {sorted(done)})")
        app, errors, warnings_ = connect_sw()
        desktop, ipk = connect_aedt()
        for n in todo:
            ipk = run_level(app, errors, warnings_, desktop, ipk, params, n)
    report(params)


if __name__ == "__main__":
    main()
