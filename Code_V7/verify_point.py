"""
V7 검증 해석 — 설계변수를 넣으면 형상(SolidWorks) → Icepak 해석(면 발열) → 결과 저장까지 한 번에 (V6 verify_point.py 기반)

캠페인(main.py)과 같은 함수를 그대로 쓴다: Solidworks.update_sw(전역변수 반영·리빌드·질량),
icepak.run_icepak(메시·물성·경계조건·측정면 전부 캠페인과 같음), result_parser.extract_and_save(지표 계산).
캠페인 결과 폴더(Result/OLHD)와 섞이지 않게 결과는 Result/VERIFY 에 두고, 파일 이름은 입력한 변수 값으로 만든다.

사용법
  1) 아래 POINTS 에 검증할 설계를 넣는다.
     · 넣은 변수만 파일 이름에 들어간다(예: in23.1_psu3_mid22_midin23.9_t1-1.7_n1-19_t2-1.6_n2-23).
     · 넣지 않은 변수는 기본값을 쓴다(_defaults): 유량 4 LPM, 유로 깊이 8 mm, 나머지는 선별로 고정된 값
       (V7 선별 결과가 있으면 그 값, 아직 없으면 V6 선별 고정값). 활성 변수는 직접 넣어야 한다.
     · pred 에 대리모델 예측과 ±2σ 범위를 넣으면 CFD 값이 그 안에 드는지 같이 판정·저장한다(선택).
       V7 지표 이름: max_temp, temp_std(채널 간), temp_in(채널 안), pressure_drop, power_module_flow, psu_margin
  2) F5(인자 없이)                                   → RUN 에 적은 번호의 설계만 (RUN 이 비어 있으면 POINTS 전부)
     python verify_point.py input_thick=23.1 power_input_thick=3 mid_thick=22 ... flow_lpm=5 fin_height=10
                                                     → 인자로 준 설계 하나만 (pred 없음)
  3) 결과: Result/VERIFY/
       results_verify.csv            설계마다 한 줄 (같은 이름을 다시 돌리면 그 줄만 덮어씀)
       result_verify_<이름>.csv       Icepak Fields Summary 원본
       flowpath_verify_<이름>.STEP    형상

⚠ 캠페인(main.py / run_forever.py)·grid_convergence.py 가 돌고 있을 때 실행하지 말 것 — 같은 SolidWorks 모델과
  AEDT 프로젝트 파일(thermal_v7.aedt)을 쓴다. 캠페인처럼 SolidWorks 모델에 마지막 설계 값이 저장된다.
"""
import os
import sys
import time

import pandas as pd

import icepak
from icepak import connect_aedt
from Solidworks import connect_sw, update_sw
from result_parser import extract_and_save, PSU_LOSS_W
from params import CANDIDATES, INT_PARAMS, C_LO, C_HI, Screening, to_dict
from fins import BANKS, bank_feasible, describe_bank
from paths import RESULT_DIR, ASM_PATH, SCREENING_PATH

VERIFY_DIR = os.path.join(RESULT_DIR, "VERIFY")
SUMMARY_PATH = os.path.join(VERIFY_DIR, "results_verify.csv")

PSI_PA = 6894.757

# 넣지 않은 변수의 기본값 — 유량·깊이는 기준 조건, 나머지는 V7 선별 고정값(_defaults). 선별 전에는 V6 선별 고정값
NOMINAL = {"flow_lpm": 4.0, "fin_height": 8.0}
V6_FIXED = {"input_angle": 150.0, "mid_angle": 115.0, "output_thick": 35.0}

# 파일 이름에 쓰는 약어 (CANDIDATES 순서로 이어 붙임)
ABBR = {"input_thick": "in", "input_angle": "ina", "power_input_thick": "psu", "mid_thick": "mid",
        "mid_angle": "mida", "mid_input_thick": "midin", "output_thick": "out",
        "fin_thick_1": "t1-", "fin_count_1": "n1-", "fin_thick_2": "t2-", "fin_count_2": "n2-",
        "flow_lpm": "q", "fin_height": "h"}


def _defaults():
    """넣지 않은 변수의 값: 유량 4 LPM · 깊이 8 mm + 선별로 고정된 변수의 값(V7 선별 결과, 없으면 V6 고정값)."""
    if os.path.exists(SCREENING_PATH):
        fixed = {n: float(v) for n, v in Screening(SCREENING_PATH).fixed_values().items()}
    else:
        fixed = dict(V6_FIXED)
    return {**NOMINAL, **fixed}

# ── 검증할 설계 ─────────────────────────────────────────────────
#   x    : 설계변수 (넣은 것만 이름에 들어감)
#   pred : {지표: (예측, 2σ 하한, 2σ 상한)} — V7 대리모델 예측. 비교가 필요 없으면 빼도 됨
#   (V7 대리모델이 아직 없어, 지금은 V6 최종 설계 두 개를 pred 없이 V7 조건으로 다시 보는 용도로 둔다)
POINTS = [
    {   # V6 최종 최적설계 (결론 장표)
        "x": {"input_thick": 23.1, "power_input_thick": 3.0, "mid_thick": 22.0, "mid_input_thick": 23.9,
              "fin_thick_1": 1.7, "fin_count_1": 19, "fin_thick_2": 1.6, "fin_count_2": 23},
    },
    {   # V6 에서 차압을 예측 +2σ 상한으로 판정했을 때의 1위
        "x": {"input_thick": 24.6, "power_input_thick": 3.0, "mid_thick": 22.1, "mid_input_thick": 25.0,
              "fin_thick_1": 1.9, "fin_count_1": 18, "fin_thick_2": 1.5, "fin_count_2": 23},
    },
]

# F5(인자 없이) 실행할 POINTS 번호 — 비워 두면 POINTS 전부
RUN = [0]


# ── 입력 정리·검사 ─────────────────────────────────────────────
def _fmt(name, v):
    return str(int(v)) if name in INT_PARAMS else f"{float(v):g}"


def make_name(x_in):
    """입력한 변수만 CANDIDATES 순서로 이어 붙인 이름."""
    return "_".join(f"{ABBR[n]}{_fmt(n, x_in[n])}" for n in CANDIDATES if n in x_in)


def build_params(x_in):
    """입력 + 기본값(_defaults) → SolidWorks·Icepak 에 넣을 params(후보 13개 + 고정 형상). 범위·갭 제약 검사."""
    unknown = [k for k in x_in if k not in CANDIDATES]
    if unknown:
        raise ValueError(f"모르는 변수: {unknown} (가능: {CANDIDATES})")
    full = {**_defaults(), **x_in}
    missing = [n for n in CANDIDATES if n not in full]
    if missing:
        raise ValueError(f"값이 없는 변수: {missing} — POINTS 의 x 에 넣을 것")
    for n, lo, hi in zip(CANDIDATES, C_LO, C_HI):
        if not lo - 1e-9 <= float(full[n]) <= hi + 1e-9:
            print(f"  ⚠ {n}={full[n]} 이 캠페인 범위 [{lo:g}, {hi:g}] 밖 — 대리모델 외삽 영역")
        if n in INT_PARAMS and float(full[n]) != int(full[n]):
            raise ValueError(f"{n}={full[n]} — 정수여야 함")
    params = to_dict([full[n] for n in CANDIDATES])
    for b in BANKS:
        if not bank_feasible(params, b):
            raise ValueError(f"갭 제약 위반: {describe_bank(params, b)}")
    return params


def _from_argv(argv):
    x = {}
    for a in argv:
        if "=" not in a:
            raise SystemExit(f"인자는 이름=값 꼴로: {a}")
        k, v = a.split("=", 1)
        x[k.strip()] = float(v)
    # POINTS 에 같은 설계가 있으면 그 예측(pred)을 같이 쓴다 — 결과 줄을 덮어써도 비교가 빠지지 않게
    same = [p for p in POINTS if make_name(p["x"]) == make_name(x)]
    return [{"x": x, "pred": same[0].get("pred") if same else None}]


# ── 형상·해석 ─────────────────────────────────────────────────
def export_step_to(app, errors, path):
    """Solidworks.export_step 과 같고 저장 경로만 받는다."""
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.SaveAs3(path, 0, 0)
    print("STEP 저장 완료:", path)
    return path


def run_point(app, errors, warnings, desktop, ipk, k, name, params):
    mass_kg, vol_mm3 = update_sw(app, errors, warnings, params)
    step_file = export_step_to(app, errors, os.path.join(VERIFY_DIR, f"flowpath_verify_{name}.STEP"))
    csv_path = os.path.join(VERIFY_DIR, f"result_verify_{name}.csv")
    # run_icepak 은 결과 CSV 경로를 paths.icepak_result_path(phase, idx) 로 정한다(캠페인 폴더).
    # 캠페인 결과를 덮어쓰지 않게, 이 해석 동안만 icepak 모듈의 경로 함수를 이 설계의 경로로 바꿔 둔다.
    original = icepak.icepak_result_path
    icepak.icepak_result_path = lambda phase, idx: csv_path
    try:
        ipk, result_path, pao_volume_mm3 = icepak.run_icepak(desktop, ipk, step_file, "verify", k, params)
    finally:
        icepak.icepak_result_path = original
    res = extract_and_save(name, params, result_path, mass_kg, vol_mm3, pao_volume_mm3)
    return ipk, res, step_file, result_path


def _row(name, params, res, pred):
    row = {"name": name, **{n: params[n] for n in CANDIDATES}}
    res = dict(res)
    res["pressure_drop_psi"] = res["pressure_drop"] / PSI_PA
    row.update(res)
    for k, (m, lo, hi) in (pred or {}).items():
        row[f"pred_{k}"] = m
        row[f"err_{k}"] = res[k] - m
        row[f"in2s_{k}"] = bool(lo <= res[k] <= hi)
    row["status"] = "ok"
    row["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return row


def _report(row, pred):
    print(f"\n[{row['name']}] 검증 결과")
    print(f"  최고온도 {row['max_temp']:.2f} °C (슬롯 {row['hot_slot']}) · 채널 간 편차 {row['temp_std']:.3f} °C · "
          f"채널 안 편차 {row['temp_in']:.3f} °C (최악 {row['temp_in_worst']:.3f} °C, 슬롯 {row['worst_in_slot']}) · "
          f"차압 {row['pressure_drop']:.0f} Pa ({row['pressure_drop_psi']:.3f} psi) · 중량 {row['weight']:.3f} kg")
    print(f"  조건: 냉각수 {row['flow_lpm']:g} LPM · 유로 깊이 {row['fin_height']:g} mm")
    print(f"  분기비 점검: 유량 {row['power_module_flow']*100:.1f}% · 에너지 보존 {row['power_module_flow_energy']*100:.1f}% · "
          f"1차 통과 후 통로 유량 {row['q_mid_ratio']*100:.0f}% (입구 유량 대비)")
    ok = row["psu_margin"] >= 0
    print(f"  전원부({PSU_LOSS_W:g} W) 분기 {row['power_module_flow']*100:.1f}% (필요 {row['psu_ratio_required']*100:.1f}%, "
          f"여유 {row['psu_margin']*100:+.1f}%p) {'충족' if ok else '⚠ 부족'} · "
          f"차압 0.5 psi {'이내' if row['pressure_drop_psi'] <= 0.5 else '⚠ 초과'}")
    for k, (m, lo, hi) in (pred or {}).items():
        print(f"  {k:18s} CFD {row[k]:.4f}  예측 {m:.4f} [{lo:.4f}, {hi:.4f}]  "
              f"{'±2σ 이내' if row[f'in2s_{k}'] else '⚠ ±2σ 밖'}")


def _save(row):
    old = pd.read_csv(SUMMARY_PATH) if os.path.exists(SUMMARY_PATH) else pd.DataFrame()
    if len(old):
        old = old[old["name"] != row["name"]]          # 같은 설계를 다시 돌리면 덮어씀
    pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(SUMMARY_PATH, index=False)


def _cleanup_projects(desktop):
    try:
        od = desktop.odesktop
        for p in list(od.GetProjectList()):
            try:
                od.CloseProject(p)
            except Exception:
                pass
    except Exception:
        pass


def main(argv):
    pts = _from_argv(argv) if argv else [POINTS[i] for i in (RUN or range(len(POINTS)))]
    jobs = []
    for p in pts:                                   # SolidWorks·AEDT 를 띄우기 전에 입력부터 전부 검사
        name = make_name(p["x"])
        jobs.append((name, build_params(p["x"]), p.get("pred")))
    os.makedirs(VERIFY_DIR, exist_ok=True)
    print("검증할 설계:", [j[0] for j in jobs])

    app, errors, warnings = connect_sw()
    desktop, ipk = connect_aedt()
    for k, (name, params, pred) in enumerate(jobs):
        print(f"\n===== {name} 시작 ({k + 1}/{len(jobs)}) {time.strftime('%H:%M:%S')} =====")
        t0 = time.time()
        try:
            ipk, res, step_file, result_path = run_point(app, errors, warnings, desktop, ipk, k, name, params)
            row = _row(name, params, res, pred)
            _report(row, pred)
        except Exception as e:
            print(f"  ⚠ [{name}] 실패: {e}")
            _cleanup_projects(desktop)
            ipk = None
            row = {"name": name, **{n: params[n] for n in CANDIDATES}, "status": f"fail: {e}",
                   "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        _save(row)
        print(f"[{name}] 소요 {time.time() - t0:.0f}초 → {SUMMARY_PATH}")

    print("\n완료:")
    cols = ["name", "status", "max_temp", "temp_std", "temp_in", "temp_in_worst", "pressure_drop_psi", "psu_margin"]
    df = pd.read_csv(SUMMARY_PATH)
    print(df[[c for c in cols if c in df.columns]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:])
