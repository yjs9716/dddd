"""
V6 격자 민감도 시험 — 핀 갭 방향(y) 격자 크기 결정 + GCI (Celik et al. 2008 / ASME V&V 20)

⚠ DSD(main.py)를 시작하기 전에 실행한다. 여기서 정한 MESH_REGION_Y 를 캠페인 전체에 고정한다.
⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks/AEDT 사용).
⚠ 결과는 Result/GCI 에 따로 저장되며 DSD/OLHD 결과와 섞이지 않는다.

무엇을 하는가
  핀 갭이 가장 좁은 "최악 조건" 설계 하나를 고정해 두고, 유체 서브리전 격자의
  y(핀 갭 방향) 최대 크기만 3단계로 바꿔 같은 설계를 3번 해석한다.
      h1(fine)   = 0.500 mm
      h2(medium) = 0.707 mm   (= 0.5·√2)
      h3(coarse) = 1.000 mm   (= 0.5·2)       공통비 r = √2
  x, z 는 icepak.py 의 값(1.0 mm) 그대로 둔다 — 결정하려는 것이 갭 방향 해상도이기 때문.
  (x·y·z 를 모두 줄이는 정식 GCI 는 셀 수가 8배까지 늘어 비현실적. 논문에는
   "갭 방향 격자 민감도"로 밝힌다.)

시험 설계 (V5 grid_convergence.py 와 같은 원칙: 갭 최소 + 나머지는 범위 중앙)
  · 1차·2차 뱅크 모두 핀 두께 1.5 mm, 핀 24개 → 갭 2.02 mm (최소 갭 2.0 mm 바로 위)
  · 나머지 변수 7개는 각자 범위의 중앙값

판단 (각 레벨이 끝날 때마다 결과를 저장하므로, 중간에 끊겨도 다시 실행하면 이어서 한다)
  · fine 대비 coarse(1.0)·medium(0.707)의 상대 차이와, 각 레벨의 GCI(수치 불확도)를 출력한다.
  · 캠페인 격자는 "모든 응답에서 fine 대비 차이가 허용치 이내인 가장 성긴 레벨"로 고른다.
    허용치는 아래 TOL_PCT, TOL_MAXT_K (사전에 정할 것).
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

MESH_LEVELS_Y = [0.5, 0.5 * 2 ** 0.5, 1.0]    # [fine, medium, coarse]
REFINEMENT_R = 2 ** 0.5
GCI_IDX_BASE = 900                              # 결과 파일 번호 (캠페인 idx와 겹치지 않게)
TOL_PCT = 2.0                                   # fine 대비 허용 차이 [%] — 실행 전에 확정
TOL_MAXT_K = 0.2                                # 최고온도는 절대 차이 [K]로 판정 (아래 주석)
#   최고온도는 절대온도(약 117 °C)라 2%면 2.3 K나 돼서 판정이 무의미해진다.
#   그래서 절대 차이로 본다. 0.2 K는 V5 대리모델이 설계 간 차이를 구분하던 문턱(약 0.17 K)과
#   같은 수준이다. 나머지 응답(차압, 온도편차, 유량편차, 분기비)은 상대 차이 TOL_PCT로 본다.

RESP = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow"]
# weight 는 SolidWorks 형상에서 나오므로 격자와 무관 — 비교에서 제외

GCI_RESULTS_PATH = os.path.join(GCI_DIR, "gci_results.csv")
GCI_SUMMARY_PATH = os.path.join(GCI_DIR, "gci_summary.json")


def test_design():
    """갭 최소 설계: 두 뱅크 모두 t=1.5mm, 24개. 나머지는 범위 중앙."""
    x = decode(np.full(N_CAND_DIM, 0.5))
    p = to_dict(x)
    for b in BANKS:
        p[f"fin_thick_{b}"] = 1.5
        p[f"fin_count_{b}"] = 24
    if not all_banks_feasible(p):
        raise RuntimeError("시험 설계가 갭 제약을 위반함 — fins.MIN_GAP_MM 확인")
    print("[GCI] 시험 설계")
    for n in CANDIDATES:
        print(f"    {n:20s} = {p[n]}")
    for b in BANKS:
        print(f"    {describe_bank(p, b)}")
    return p


def _load():
    if os.path.exists(GCI_RESULTS_PATH):
        return pd.read_csv(GCI_RESULTS_PATH)
    return pd.DataFrame(columns=["level", "mesh_y_mm"] + RESP)


def _save_level(level, mesh_y, results):
    df = _load()
    df = df[df["level"] != level]
    row = {"level": level, "mesh_y_mm": mesh_y, **{k: results[k] for k in RESP}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("level")
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(GCI_RESULTS_PATH, index=False)


def run_level(app, errors, warnings_, desktop, ipk, params, level, mesh_y):
    print(f"\n{'='*70}\n[GCI] 레벨 {level}: mesh y = {mesh_y:.3f} mm "
          f"(x={icepak.MESH_REGION_X}, z={icepak.MESH_REGION_Z})\n{'='*70}")
    icepak.MESH_REGION_Y = mesh_y            # 이 프로세스 안에서만 덮어씀 (파일은 안 바뀜)
    idx = GCI_IDX_BASE + level
    t0 = time.time()
    al_mass, al_vol = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, "gci", idx)
    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    results = extract_and_save(f"gci:{level}", params, result_path, al_mass, al_vol)
    _save_level(level, mesh_y, results)
    print(f"[GCI] 레벨 {level} 완료 ({(time.time()-t0)/60:.0f}분)")
    return ipk


def gci(f1, f2, f3, r=REFINEMENT_R, Fs=1.25):
    """Celik et al. (2008). f1=fine, f2=medium, f3=coarse.
    반환: p(겉보기 수렴차수), f_ext(외삽값), GCI_fine[%], GCI_coarse[%](=coarse 단 불확도), note"""
    e21, e32 = f2 - f1, f3 - f2
    if abs(e21) < 1e-14:
        return dict(p=np.nan, f_ext=f1, gci_fine=0.0, gci_coarse=100 * abs(e32 / f3) * Fs, note="f1≈f2")
    s = e32 / e21
    if s <= 0:
        return dict(p=np.nan, f_ext=np.nan, gci_fine=np.nan,
                    gci_coarse=100 * Fs * abs(e32 / f3), note="진동수렴 — |f3−f2| 로 보수 추정")
    p = abs(math.log(abs(s))) / math.log(r)
    rp = r ** p
    f_ext = (rp * f1 - f2) / (rp - 1)
    gci_fine = 100 * Fs * abs(e21 / f1) / (rp - 1)
    gci_coarse = 100 * Fs * abs(e32 / f2) * rp / (rp - 1)
    return dict(p=p, f_ext=f_ext, gci_fine=gci_fine, gci_coarse=gci_coarse, note="")


def report():
    df = _load().set_index("level")
    if len(df) < 3:
        print(f"[GCI] 레벨 {len(df)}/3 완료 — 나머지를 마저 돌릴 것")
        return
    f1, f2, f3 = df.loc[0, RESP], df.loc[1, RESP], df.loc[2, RESP]
    print(f"\n{'='*96}\n[GCI] 결과 (y 격자: fine 0.5 / medium 0.707 / coarse 1.0 mm)\n{'='*96}")
    print(f"{'응답':18s} {'fine':>11s} {'medium':>11s} {'coarse':>11s} {'med차%':>7s} {'coa차%':>7s} "
          f"{'p':>5s} {'GCI_f%':>7s} {'GCI_c%':>7s}  비고")
    summary, ok_med, ok_coa = {}, True, True
    for k in RESP:
        g = gci(f1[k], f2[k], f3[k])
        dm = 100 * (f2[k] - f1[k]) / f1[k]
        dc = 100 * (f3[k] - f1[k]) / f1[k]
        if k == "max_temp":
            ok_med &= abs(f2[k] - f1[k]) <= TOL_MAXT_K
            ok_coa &= abs(f3[k] - f1[k]) <= TOL_MAXT_K
        else:
            ok_med &= abs(dm) <= TOL_PCT
            ok_coa &= abs(dc) <= TOL_PCT
        summary[k] = dict(fine=f1[k], medium=f2[k], coarse=f3[k], diff_medium_pct=dm, diff_coarse_pct=dc, **g)
        fmt = lambda v, d=2: "N/A" if v != v else f"{v:.{d}f}"
        print(f"{k:18s} {f1[k]:11.5g} {f2[k]:11.5g} {f3[k]:11.5g} {dm:7.2f} {dc:7.2f} "
              f"{fmt(g['p']):>5s} {fmt(g['gci_fine']):>7s} {fmt(g['gci_coarse']):>7s}  {g['note']}")
    pick = 1.0 if ok_coa else (0.5 * 2 ** 0.5 if ok_med else 0.5)
    print(f"\n  최고온도 절대 차이: medium {f2['max_temp']-f1['max_temp']:+.3f} K, "
          f"coarse {f3['max_temp']-f1['max_temp']:+.3f} K (허용 ±{TOL_MAXT_K} K)")
    print(f"\n허용 차이 {TOL_PCT}% (최고온도 {TOL_MAXT_K} K) 기준 권장 MESH_REGION_Y = {pick:.3f} mm "
          f"(coarse 통과: {ok_coa}, medium 통과: {ok_med})")
    print("  ※ 유량편차(std_pass1/2)는 값 자체가 작아 상대 차이가 크게 보일 수 있다 — 절대 차이도 함께 볼 것")
    with open(GCI_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump({"mesh_levels_y": MESH_LEVELS_Y, "tol_pct": TOL_PCT, "tol_maxt_k": TOL_MAXT_K,
                   "recommended_mesh_y": pick, "responses": summary}, f, ensure_ascii=False, indent=2,
                  default=float)
    print(f"요약 저장: {GCI_SUMMARY_PATH}")


def main():
    params = test_design()
    done = set(_load()["level"].astype(int)) if len(_load()) else set()
    todo = [i for i in range(len(MESH_LEVELS_Y)) if i not in done]
    if todo:
        app, errors, warnings_ = connect_sw()
        desktop, ipk = connect_aedt()
        for level in todo:
            ipk = run_level(app, errors, warnings_, desktop, ipk, params, level, MESH_LEVELS_Y[level])
    report()


if __name__ == "__main__":
    main()
