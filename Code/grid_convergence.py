"""
격자수렴성시험(GCI, ASME V&V 20) — U_j(CFD 재현 불확도) 산출용 스크립트

⚠ 캠페인(main.py)이 끝난 뒤에 실행할 것 — 같은 SolidWorks/AEDT를 쓰므로 동시 실행 불가.
⚠ results_v5.csv에는 안 섞임 — 이 스크립트 전용 결과파일(GCI_RESULTS_PATH)에 따로 저장.

무엇을 하는가
  갭이 최소(2.5mm, 갭 제약의 하한 — 메시 해상도가 제일 빡빡한 "최악 조건")인 설계
  하나를 고정해두고, 메시 크기만 3단계(성김→촘촘)로 바꿔가며 같은 설계를 3번
  해석한다. 그 3개 결과로 리처드슨 외삽 + GCI를 계산해서, "지금 캠페인이 쓰는
  고정 메시(1.0mm)로 얻은 값이 진짜 값(메시 무한히 촘촘할 때)에서 얼마나
  벗어나는가"를 정량화한다 — 이게 U_j (목적함수별 CFD 재현 불확도).

가변메시로 전환할 경우
  이 스크립트는 "고정 1.0mm 메시" 전제로 짠 것이라, 가변메시로 바꾸면 무효.
  가변메시 스킴을 확정한 뒤, 각 구간(tier)의 대표 설계로 이 스크립트를 다시
  돌려야 한다(icepak.py의 MESH_REGION_* 대신 각 구간의 목표값을 MESH_LEVELS에 넣으면 됨).

메시 3단계 선택 근거
  현재 캠페인이 쓰는 값(1.0mm)을 "제일 성긴(coarse)" 단계로 두고, 그보다 촘촘한
  두 단계를 등비(r=√2)로 잡았다. 이러면 "지금 실제로 쓰고 있는 그 메시"에서의
  오차를 직접 추정할 수 있다(그냥 임의의 3단계를 잡으면 현재 캠페인과 무관한
  숫자가 나옴).
      h1(fine)   = 0.500mm
      h2(medium) = 0.707mm   (= 0.5 * sqrt(2))
      h3(coarse) = 1.000mm   (= 0.5 * 2)   ← 현재 캠페인 값과 동일
"""
import time
from Solidworks import connect_sw, update_sw, export_step
import icepak
from icepak import connect_aedt, run_icepak
from result_parser import extract_and_save
from OLHD import PARAM_NAMES, LO, HI, FIXED_PARAMS, I_FIN_THICK, I_FIN_COUNT
from fins import fin_gap, is_feasible

# ── 결과 저장 위치 (캠페인 결과와 완전히 분리) ──
GCI_RESULTS_DIR  = r"E:\Thermal_Anlaysis\Liquid_plate\260827\Result"
GCI_RESULTS_PATH = GCI_RESULTS_DIR + r"\gci_results.csv"

# ── 메시 3단계 (mm) — 등비 r=sqrt(2), coarse가 현재 캠페인 값과 동일 ──
MESH_LEVELS = [0.5, 0.5 * (2 ** 0.5), 1.0]   # [fine, medium, coarse]
REFINEMENT_R = 2 ** 0.5                        # h(i+1)/h(i) 공통비

# GCI idx는 실제 캠페인 idx(0~)와 안 겹치게 900번대 사용
GCI_IDX_BASE = 900

OBJS = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2",
        "power_module_flow", "weight"]


def worst_case_params():
    """갭이 정확히 하한(2.5mm)이 되는 설계. 나머지 7개 자유변수는 각자 범위의 중앙값."""
    mid = {n: float((lo + hi) / 2.0) for n, lo, hi in zip(PARAM_NAMES, LO, HI)}
    mid["fin_thick"] = 1.5    # 하한
    mid["fin_count"] = 21     # 상한 → gap = (86.5 - 21*1.5)/22 = 2.500mm (하한과 정확히 일치)
    mid.update(FIXED_PARAMS)

    g = fin_gap(mid["fin_thick"], mid["fin_count"])
    assert is_feasible(mid["fin_thick"], mid["fin_count"]), f"갭 제약 위반: gap={g}"
    print(f"[GCI] 시험 설계 확정 — gap={g:.4f}mm (하한 2.5mm과 일치해야 정상)")
    for n in PARAM_NAMES:
        print(f"    {n:20s} = {mid[n]}")
    return mid


def run_one_mesh_level(app, errors, warnings_, desktop, ipk, params, mesh_mm, level_idx):
    """메시 크기 하나로 SolidWorks→Icepak→파싱까지 한 번 수행."""
    print(f"\n{'='*70}\n[GCI] 레벨 {level_idx}: mesh = {mesh_mm:.4f}mm 로 해석 시작\n{'='*70}")

    # icepak.py는 MESH_REGION_X/Y/Z를 모듈 전역값으로 읽으므로, 여기서 덮어써서 주입.
    # 파일(icepak.py) 자체는 안 건드림 — 이 프로세스 안에서만 유효.
    icepak.MESH_REGION_X = mesh_mm
    icepak.MESH_REGION_Y = mesh_mm
    icepak.MESH_REGION_Z = mesh_mm

    idx = GCI_IDX_BASE + level_idx
    t0 = time.time()

    aluminum_mass_kg, aluminum_volume_mm3 = update_sw(app, errors, warnings_, params)
    step_file = export_step(app, errors, idx)

    ipk, result_path, _ = run_icepak(desktop, ipk, step_file, idx, params)
    results = extract_and_save(idx, params, result_path, aluminum_mass_kg, aluminum_volume_mm3)

    print(f"[GCI] 레벨 {level_idx} 완료 ({time.time()-t0:.0f}초): mesh={mesh_mm:.4f}mm")
    for k in OBJS:
        print(f"    {k:18s} = {results[k]:.6f}")

    return ipk, results


def richardson_gci(f1, f2, f3, r=REFINEMENT_R, Fs=1.25):
    """
    ASME V&V 20 격자수렴지수.
      f1, f2, f3 : fine, medium, coarse 해석값 (h1<h2<h3, 등비 r)
      Fs         : 안전계수(3단계 시험 권장값 1.25)

    반환: dict(p=겉보기 수렴차수, f_exact=외삽값, U_coarse=coarse(=현재 캠페인) 단에서의
               불확도 — 이게 곧 그 목적함수의 U_j)
    """
    import math
    eps32 = f3 - f2
    eps21 = f2 - f1

    if abs(eps21) < 1e-12:
        # f1≈f2 — 이미 fine/medium이 사실상 같음 → medium 단에서 사실상 수렴
        return {"p": float("nan"), "f_exact": f2, "U_j": abs(f3 - f2), "note": "f1≈f2 (사실상 수렴)"}

    ratio = eps32 / eps21
    if ratio <= 0:
        # 진동수렴(oscillatory) — 단조 수렴 가정이 깨짐. p를 못 구하므로 보수적으로
        # coarse-medium 차이 자체를 U_j로 씀.
        return {"p": float("nan"), "f_exact": float("nan"), "U_j": abs(eps32),
                "note": "⚠ 진동수렴 의심 — p 산출 불가, |f3-f2|를 보수적 U_j로 사용"}

    p = math.log(ratio) / math.log(r)
    f_exact = f1 + eps21 / (r ** p - 1)
    U_coarse = Fs * abs(eps32) * (r ** p) / (r ** p - 1)   # coarse(=현재 캠페인 메시) 단 불확도

    return {"p": p, "f_exact": f_exact, "U_j": U_coarse, "note": ""}


def main():
    params = worst_case_params()

    app, errors, warnings_ = connect_sw()
    desktop, ipk = connect_aedt()

    all_results = {}   # {mesh_mm: {obj: value}}
    for i, mesh_mm in enumerate(MESH_LEVELS):
        ipk, res = run_one_mesh_level(app, errors, warnings_, desktop, ipk, params, mesh_mm, i)
        all_results[mesh_mm] = res

    f1 = all_results[MESH_LEVELS[0]]   # fine
    f2 = all_results[MESH_LEVELS[1]]   # medium
    f3 = all_results[MESH_LEVELS[2]]   # coarse = 현재 캠페인 메시(1.0mm)

    print(f"\n\n{'='*78}\n[GCI] 최종 결과 — U_j (현재 캠페인 메시 1.0mm 기준 불확도)\n{'='*78}")
    print(f"{'목적함수':18s} {'fine(0.5)':>12s} {'medium(0.71)':>13s} {'coarse(1.0)':>12s} "
          f"{'p':>6s} {'외삽값':>12s} {'U_j':>10s}  비고")
    U_j_table = {}
    for k in OBJS:
        g = richardson_gci(f1[k], f2[k], f3[k])
        U_j_table[k] = g["U_j"]
        p_str = f"{g['p']:.2f}" if g["p"] == g["p"] else "N/A"
        fe_str = f"{g['f_exact']:.5f}" if g["f_exact"] == g["f_exact"] else "N/A"
        print(f"{k:18s} {f1[k]:12.5f} {f2[k]:13.5f} {f3[k]:12.5f} "
              f"{p_str:>6s} {fe_str:>12s} {g['U_j']:10.5f}  {g['note']}")

    print(f"\n다음 단계: 이 U_j 값들을 ML.py의 TERMINATION_GROUPS 절대오차 기준으로 반영할 것")
    print(f"           (pressure_drop/temp_std/max_temp도 상대오차 대신 절대오차 |pred-실측|<=U_j로 통일 검토)")

    import json
    with open(GCI_RESULTS_DIR + r"\gci_summary.json", "w", encoding="utf-8") as f:
        json.dump({"params": params, "mesh_levels": MESH_LEVELS,
                   "raw": {str(m): all_results[m] for m in MESH_LEVELS},
                   "U_j": U_j_table}, f, indent=2, ensure_ascii=False)
    print(f"\n요약 저장: {GCI_RESULTS_DIR}\\gci_summary.json")


if __name__ == "__main__":
    main()
