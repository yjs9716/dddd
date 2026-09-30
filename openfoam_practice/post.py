# -*- coding: utf-8 -*-
"""
[4단계] 후처리: postProcessing/ 에서 목적함수와 검증 지표 추출

사용법:  python post.py runs/case_000

뽑는 값
  - 목적함수: 고체 최고 온도, 압력강하
  - 열수지: 유체가 가져간 열량 = mdot * cp * (T_out - T_in)  vs  발열량
  - 수렴 지표: 마지막 구간에서 최고 온도, 압력강하가 얼마나 변했는지
"""
import json
import re
import sys
from pathlib import Path


def read_series(path, col):
    """OpenFOAM .dat 파일에서 (반복 번호, 값) 목록. col은 탭 구분 열 번호."""
    out = {}
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        f = [s.strip() for s in line.split("\t")]
        out[float(f[0])] = float(f[col])  # 같은 반복이 두 번 쓰이면 마지막 값
    return sorted(out.items())


def pp(case, region, name, fname):
    return case / "postProcessing" / region / name / "0" / fname


def fluid_cp(case):
    text = (case / "constant" / "fluid" / "thermophysicalProperties").read_text()
    return float(re.search(r"\bCp\s+([0-9.eE+-]+)\s*;", text).group(1))


def change_over_tail(series, frac=0.1):
    """마지막 frac 구간에서 값의 (최대 - 최소)"""
    n = max(2, int(len(series) * frac))
    vals = [v for _, v in series[-n:]]
    return max(vals) - min(vals)


def n_cells(case, region):
    log = case / f"log.checkMesh.{region}"
    if not log.exists():
        return None
    m = re.search(r"^\s+cells:\s+(\d+)", log.read_text(), re.M)
    return int(m.group(1)) if m else None


def summarize(case):
    case = Path(case)
    p = json.load(open(case / "params.json"))

    Tmax = read_series(pp(case, "solid", "solidTmax", "fieldMinMax.dat"), 4)
    p_in = read_series(pp(case, "fluid", "pIn", "surfaceFieldValue.dat"), 1)
    p_out = read_series(pp(case, "fluid", "pOut", "surfaceFieldValue.dat"), 1)
    mdot = read_series(pp(case, "fluid", "mdotOut", "surfaceFieldValue.dat"), 1)
    T_out = read_series(pp(case, "fluid", "TOut", "surfaceFieldValue.dat"), 1)
    q_wall = read_series(pp(case, "fluid", "wallHeatFlux", "wallHeatFlux.dat"), 4)

    dp = [(t, a - b) for (t, a), (_, b) in zip(p_in, p_out)]
    cp = fluid_cp(case)
    Q_fluid = mdot[-1][1] * cp * (T_out[-1][1] - p["T_in_K"])
    Q_heater = p["Q_heater_W"]

    return {
        "iterations": int(Tmax[-1][0]),
        "cells_fluid": n_cells(case, "fluid"),
        "cells_solid": n_cells(case, "solid"),
        # 목적함수
        "Tmax_solid_C": Tmax[-1][1] - 273.15,
        "dp_Pa": dp[-1][1],
        # 열수지
        "mdot_kg_s": mdot[-1][1],
        "T_out_C": T_out[-1][1] - 273.15,
        "Q_heater_W": Q_heater,
        "Q_fluid_W": Q_fluid,
        "Q_wall_W": q_wall[-1][1],
        "energy_balance_err_pct": (Q_fluid - Q_heater) / Q_heater * 100,
        # 수렴 지표 (마지막 10% 반복 동안의 변동폭)
        "tail_change_Tmax_K": change_over_tail(Tmax),
        "tail_change_dp_pct": change_over_tail(dp) / abs(dp[-1][1]) * 100,
    }


def report(r):
    ok_bal = abs(r["energy_balance_err_pct"]) < 2
    ok_conv = r["tail_change_Tmax_K"] < 0.01 and r["tail_change_dp_pct"] < 0.1
    print()
    print("=========== 결과 요약 ===========")
    print(f" 반복 {r['iterations']}회, 셀 수 fluid {r['cells_fluid']} / solid {r['cells_solid']}")
    print(f" [목적] 고체 최고 온도 : {r['Tmax_solid_C']:.3f} °C")
    print(f" [목적] 압력강하       : {r['dp_Pa']:.1f} Pa")
    print(" ---- 열수지 ----")
    print(f" 발열량               : {r['Q_heater_W']:.3f} W")
    print(f" 유체가 가져간 열량   : {r['Q_fluid_W']:.3f} W  (mdot*cp*ΔT)")
    print(f" 접촉면 통과 열량     : {r['Q_wall_W']:.3f} W")
    print(f" 열수지 오차          : {r['energy_balance_err_pct']:+.2f} %  -> {'OK' if ok_bal else '확인 필요'}")
    print(" ---- 수렴 ----")
    print(f" 마지막 10% 구간 최고온도 변동 : {r['tail_change_Tmax_K']:.4f} K")
    print(f" 마지막 10% 구간 압력강하 변동 : {r['tail_change_dp_pct']:.4f} %  -> {'OK' if ok_conv else '반복 더 필요'}")
    print("=================================")


if __name__ == "__main__":
    case = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/case_000")
    res = summarize(case)
    report(res)
