"""
V7 캠페인 전 점검 — 최종 해석 조건(면 발열 17개 · 680 W · 출구 역류 차단)에서 격자 3단계 + 재현성 + 모서리

⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks/AEDT 사용).
⚠ 결과는 Result/GCI 에 따로 저장되며 캠페인 결과와 섞이지 않는다.
⚠ 해석이 하나 끝날 때마다 저장하므로, 중간에 끊겨도 다시 실행하면 남은 것부터 이어서 한다.
      python grid_convergence.py           → 남은 해석 전부 + 보고
      python grid_convergence.py report    → 해석 없이 지금까지 결과로 보고만

V6 격자 시험과 다른 점 (V6 의 약점을 메운다)
  · V6 는 y·z 를 따로 한 축씩 바꿨고 x 는 바꾸지 않았다. 해석 조건도 최종 캠페인과 달랐다(역류 허용·발열 9개).
    V7 은 최종 조건 그대로, 유체 서브리전과 분기 입구 국소 메시의 x·y·z 셀 크기를 같은 배율로 함께 바꾼다
    (배율 COARSE · 1 · FINE — 1 이 캠페인 값). 판(알루미늄)도 서브리전 안이라 함께 촘촘해진다.
  · 설계 셋으로 돈다.
      v6opt  : V6 최종 최적설계, 4 LPM · 깊이 8 mm (실제로 최적점이 있을 법한 영역)
      tight  : 두 뱅크 모두 핀 1.5 mm × 24개(갭 2.02 mm, 가장 촘촘), 4 LPM · 깊이 8 mm, 나머지는 범위 중앙
               — v6opt 와 같은 유량·깊이라 둘의 차이가 "같은 조건에서 설계끼리의 차이"(잡음/신호의 신호)가 된다
      corner : 메시에 가장 까다로운 모서리 — 최대 유량 6 LPM(가장 빠른 유속) · 최소 깊이 6 mm(z 칸이 가장 작음)
               · 핀 1.5 mm × 24개 · 분기 입구 폭 3 mm(가장 좁은 통로). 여기서 통과하면 범위 전체를 통과한다고 본다
  · 재현성: v6opt 를 캠페인 값 격자로 한 번 더 돌린다(repeat). 입력이 같으면 결과도 같아야 한다.
  · 모두 10회. 선별(DSD) 전에 도는 점검이라 각도·출구 폭은 V6 선별 고정값(V6_FIXED)으로 둔다.

보고 내용
  · 지표별 세 격자 값, 캠페인 격자(1) 대비 조밀 격자 차이, GCI (Celik et al. 2008, 격자 비가 다를 때의 반복식)
  · 잡음/신호 = |조밀 − 캠페인 격자| ÷ |두 설계의 차이| — 작을수록 캠페인 격자로 설계를 구분하기에 충분하다.
    채널 안 편차는 최고−최저(기본)가 기준 안이면 그대로, 넘고 표준편차는 기준 안이면 표준편차를 권한다.
  · 재현성 = |repeat − 캠페인 격자|
  · 분기비 교차 확인 — 유량 측정(정규화) vs 에너지 보존, Q_mid ÷ 유량(단면 유량 측정 편향)
판정 기준(권장): 차압·분기비는 조밀 격자 대비 2% 이내, 온도 셋은 잡음/신호 0.1 이하. 넘으면 icepak.py 의
  MESH_REGION_* 를 줄이고 이 점검을 다시 한다(결과 파일을 지우고 — 기준 메시가 바뀌면 이어서 하지 않고 멈춘다).
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

# ══════════════ 점검 설정 — 실행 전에 확정 ══════════════
COARSE, FINE = 1.3, 1 / 1.3          # 셀 크기 배율 (1 = icepak.py 캠페인 값). 조밀 격자는 셀 수 약 2.2배
LEVELS = {"coarse": COARSE, "medium": 1.0, "fine": FINE, "repeat": 1.0}
DESIGNS = ["v6opt", "tight", "corner"]   # 돌릴 설계 (아래 test_designs). 앞의 두 개로 잡음/신호를 본다
REPEAT_DESIGN = "v6opt"               # 재현성 확인 설계
TOL_PCT = 2.0                         # 차압·분기비 허용 차이 [%] (조밀 격자 대비)
TOL_NOISE_SIGNAL = 0.1                # 온도 지표 잡음/신호 허용치
V6_OPT = {"input_thick": 23.1, "power_input_thick": 3.0, "mid_thick": 22.0, "mid_input_thick": 23.9,
          "fin_thick_1": 1.7, "fin_count_1": 19, "fin_thick_2": 1.6, "fin_count_2": 23,
          "flow_lpm": 4.0, "fin_height": 8.0}
V6_FIXED = {"input_angle": 150.0, "mid_angle": 115.0, "output_thick": 35.0}   # V6 선별 고정값
# ═══════════════════════════════════════════════════════

RESULTS_PATH = os.path.join(GCI_DIR, "gci_v7_results.csv")
SUMMARY_PATH = os.path.join(GCI_DIR, "gci_v7_summary.json")
TEMP_RESP = ["max_temp", "temp_std", "temp_in_range", "temp_in_sd", "temp_in_worst"]
FLOW_RESP = ["pressure_drop", "power_module_flow"]
CHECK_RESP = ["power_module_flow_energy", "q_mid_ratio", "T_pass1", "T_outlet", "T_pass2"]
RESP = TEMP_RESP + FLOW_RESP + CHECK_RESP
MESH_KEYS = ["MESH_REGION_X", "MESH_REGION_Y", "MESH_REGION_Z", "PM_MESH_X", "PM_MESH_Y", "PM_MESH_Z"]
BASE_MESH = {k: getattr(icepak, k) for k in MESH_KEYS}       # 캠페인 값 (import 시점)


def _setup():
    """해석 조건 + 캠페인 기준 메시 — 바뀌면 기존 결과와 비교할 수 없다."""
    m = "/".join(f"{BASE_MESH[k]:g}" for k in MESH_KEYS)
    return f"면발열{icepak.N_SOURCE}개·{icepak.SOURCE_POWER_W:g}W·기준메시 {m}"


def test_designs():
    mid = to_dict(decode(np.full(N_CAND_DIM, 0.5)))
    tight = {**mid, **V6_FIXED, "flow_lpm": 4.0, "fin_height": 8.0}   # 형상은 범위 중앙, 유량·깊이는 v6opt 와 같게
    for b in BANKS:
        tight[f"fin_thick_{b}"], tight[f"fin_count_{b}"] = 1.5, 24
    corner = {**tight, "flow_lpm": 6.0, "fin_height": 6.0, "power_input_thick": 3.0}
    v6 = to_dict([{**V6_FIXED, **V6_OPT}[n] for n in CANDIDATES])
    out = {"v6opt": v6, "tight": tight, "corner": corner}
    for name, p in out.items():
        if not all_banks_feasible(p):
            raise RuntimeError(f"시험 설계 {name} 가 갭 제약을 위반함")
    return out


def _load():
    if os.path.exists(RESULTS_PATH):
        return pd.read_csv(RESULTS_PATH)
    return pd.DataFrame(columns=["design", "level", "scale", "setup", "minutes", "minutes_icepak", "elements"] + RESP)


def _check_setup(df):
    if len(df) and set(df["setup"]) != {_setup()}:
        raise SystemExit(
            f"기존 결과는 {sorted(set(df['setup']))} 조건인데 지금 icepak.py 는 {_setup()} 이다.\n"
            f"  섞이면 비교가 안 된다 — 새 조건으로 처음부터 하려면 {RESULTS_PATH} 를 지우고 다시 돌릴 것.")


def _save(row):
    df = _load()
    if len(df):
        df = df[~((df["design"] == row["design"]) & (df["level"] == row["level"]))]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(GCI_DIR, exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False)


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


def _apply_mesh(scale):
    """icepak.py 의 모듈 상수를 이 프로세스 안에서만 덮어씀 (파일은 바뀌지 않음)."""
    for k in MESH_KEYS:
        setattr(icepak, k, BASE_MESH[k] * scale)


def run_one(app, errors, warnings_, desktop, ipk, design, params, level, idx):
    scale = LEVELS[level]
    _apply_mesh(scale)
    print(f"\n{'='*72}\n[점검] 설계 {design} · 격자 {level} (배율 {scale:.3f}: x {icepak.MESH_REGION_X:.3g} · "
          f"y {icepak.MESH_REGION_Y:.3g} · z {icepak.MESH_REGION_Z:.3g} mm)\n{'='*72}")
    t0 = time.time()
    al_mass, al_vol = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, "gci", idx)
    t1 = time.time()
    ipk, result_path, pao_volume_mm3 = run_icepak(desktop, ipk, step_file, "gci", idx, params)
    t2 = time.time()
    res = extract_and_save(f"gci:{design}:{level}", params, result_path, al_mass, al_vol, pao_volume_mm3)
    elements, source = _mesh_elements(ipk, idx)
    row = {"design": design, "level": level, "scale": scale, "setup": _setup(),
           "minutes": (time.time() - t0) / 60, "minutes_icepak": (t2 - t1) / 60, "elements": elements,
           **{k: res.get(k, np.nan) for k in RESP}}
    _save(row)
    el = f"{elements:,.0f}개 ({source})" if elements == elements else "읽기 실패 — AEDT 메시 정보에서 직접 적을 것"
    print(f"[점검] {design}·{level} 완료 — 전체 {row['minutes']:.0f}분 (Icepak {row['minutes_icepak']:.0f}분), 요소 {el}")
    _apply_mesh(1.0)
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
        return dict(p=np.nan, f_ext=np.nan, gci_fine=100 * 1.25 * abs(e21 / f1), note="진동수렴 — 차이로만")
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


def _h(row):
    """대표 격자 크기 — 요소 수가 있으면 N^(-1/3), 없으면 셀 크기 배율."""
    n = row.get("elements", np.nan)
    return float(n) ** (-1 / 3) if n == n and n > 0 else float(row["scale"])


def report():
    df = _load()
    if not len(df):
        print("결과가 아직 없습니다.")
        return
    out = {"setup": _setup(), "levels": LEVELS, "designs": {}, "noise_signal": {}, "repeat": {}}
    get = lambda d, lv: df[(df["design"] == d) & (df["level"] == lv)]
    for d in DESIGNS:
        rows = {lv: get(d, lv).iloc[0] for lv in ("fine", "medium", "coarse") if len(get(d, lv))}
        if not rows:
            continue
        print(f"\n{'='*100}\n[점검 결과] 설계 {d} — 격자별 값 (괄호: 캠페인 격자 대비 조밀 격자 차이)\n{'='*100}")
        print(f"{'지표':26s} " + " ".join(f"{lv:>12s}" for lv in rows) + f" {'조밀−캠페인':>14s} {'GCI(%)':>8s}  비고")
        info = {}
        for k in RESP:
            vals = {lv: float(r[k]) for lv, r in rows.items()}
            diff = vals["fine"] - vals["medium"] if {"fine", "medium"} <= set(vals) else np.nan
            g = {}
            if len(rows) == 3 and all(np.isfinite(list(vals.values()))):
                g = gci_three(tuple(_h(rows[lv]) for lv in ("fine", "medium", "coarse")),
                              tuple(vals[lv] for lv in ("fine", "medium", "coarse")))
            rel = 100 * diff / vals["fine"] if vals.get("fine") else np.nan
            info[k] = {"values": vals, "fine_minus_medium": diff, "rel_pct": rel, "gci": g}
            d_txt = f"{diff:+.4g}" + ("" if k in TEMP_RESP or k.startswith("T_") else f" ({rel:+.1f}%)")
            judge = ""
            if k in FLOW_RESP and np.isfinite(rel):
                judge = "통과" if abs(rel) <= TOL_PCT else f"⚠ {TOL_PCT}% 초과"
            print(f"{k:26s} " + " ".join(f"{vals.get(lv, np.nan):12.5g}" for lv in rows) + f" {d_txt:>14s} "
                  f"{g.get('gci_fine', np.nan):8.2f}  {' · '.join(t for t in (judge, g.get('note', '')) if t)}")
        out["designs"][d] = info

    # 잡음/신호 — 격자 오차가 두 설계의 차이에 비해 얼마나 작은가
    if all(d in out["designs"] for d in DESIGNS[:2]):
        a, b = (out["designs"][d] for d in DESIGNS[:2])
        print(f"\n[잡음/신호] |조밀 − 캠페인 격자| ÷ |{DESIGNS[0]} − {DESIGNS[1]}| (캠페인 격자 값). "
              f"{TOL_NOISE_SIGNAL:g} 이하면 캠페인 격자로 설계를 충분히 구분한다")
        for k in TEMP_RESP + FLOW_RESP:
            signal = abs(a[k]["values"].get("medium", np.nan) - b[k]["values"].get("medium", np.nan))
            noise = max(abs(a[k]["fine_minus_medium"]), abs(b[k]["fine_minus_medium"]))
            ratio = noise / signal if signal > 0 else np.inf
            out["noise_signal"][k] = {"noise": noise, "signal": signal, "ratio": ratio}
            mark = "" if not np.isfinite(ratio) or ratio <= TOL_NOISE_SIGNAL else "  ⚠ 큼"
            print(f"  {k:26s} 잡음 {noise:10.4g}  신호 {signal:10.4g}  비 {ratio:6.3f}{mark}")
        r_range = out["noise_signal"]["temp_in_range"]["ratio"]
        r_sd = out["noise_signal"]["temp_in_sd"]["ratio"]
        # 기본은 최고−최저(range). range 가 기준을 넘고 표준편차는 기준 안이면 sd, 둘 다 넘으면 메시부터 줄인다
        if r_range <= TOL_NOISE_SIGNAL:
            pick = "range"
        elif r_sd <= TOL_NOISE_SIGNAL:
            pick = "sd"
        else:
            pick = None
        out["temp_in_kind_recommended"] = pick
        ratios = f"(최고−최저 비 {r_range:.3f} / 표준편차 비 {r_sd:.3f}, 기준 {TOL_NOISE_SIGNAL:g})"
        if pick:
            print(f"  → 채널 안 편차 권장 정의: TEMP_IN_KIND = \"{pick}\" {ratios}")
        else:
            print(f"  → 채널 안 편차 두 정의 모두 기준 초과 {ratios} — icepak.py 의 MESH_REGION_* 를 줄이고 다시 점검")

    # 재현성
    rep, med = get(REPEAT_DESIGN, "repeat"), get(REPEAT_DESIGN, "medium")
    if len(rep) and len(med):
        print(f"\n[재현성] {REPEAT_DESIGN} 캠페인 격자 두 번 — 차이")
        for k in RESP:
            dv = float(rep.iloc[0][k]) - float(med.iloc[0][k])
            out["repeat"][k] = dv
            print(f"  {k:26s} {dv:+.3g}")

    # 분기비 교차 확인
    print("\n[분기비 교차 확인] 유량 측정(정규화) · 에너지 보존 · Q_mid÷유량")
    for _, r in df.sort_values(["design", "scale"]).iterrows():
        print(f"  {r['design']:6s} {r['level']:7s} 유량 {r['power_module_flow']*100:6.2f}%  에너지 "
              f"{r['power_module_flow_energy']*100:6.2f}%  Q_mid {r['q_mid_ratio']*100:5.1f}%  "
              f"요소 {r['elements'] if r['elements'] == r['elements'] else '-'}")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=float)
    print(f"\n요약 저장: {SUMMARY_PATH}")


def main():
    designs = test_designs()
    df = _load()
    _check_setup(df)
    jobs = []
    for i, d in enumerate(DESIGNS):
        for j, lv in enumerate(LEVELS):
            if lv == "repeat" and d != REPEAT_DESIGN:
                continue
            if len(df) and ((df["design"] == d) & (df["level"] == lv)).any():
                continue
            jobs.append((d, lv, 950 + 10 * i + j))
    print("[점검] 시험 설계")
    for d in DESIGNS:
        print(f"  {d}: " + "  ".join(f"{n}={designs[d][n]}" for n in CANDIDATES))
        for b in BANKS:
            print(f"      {describe_bank(designs[d], b)}")
    print(f"[점검] 남은 해석 {len(jobs)}개: {[(d, lv) for d, lv, _ in jobs]}")
    if jobs:
        app, errors, warnings_ = connect_sw()
        desktop, ipk = connect_aedt()
        for d, lv, idx in jobs:
            ipk = run_one(app, errors, warnings_, desktop, ipk, d, designs[d], lv, idx)
    report()


if __name__ == "__main__":
    if sys.argv[1:] == ["report"]:
        report()
    else:
        main()
