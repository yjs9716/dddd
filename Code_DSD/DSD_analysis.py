"""
V6 1단계 — DSD 29회 결과 분석 → 선별 판정 → screening_decision.json

⚠ 판정 규칙은 실험 전에 고정한다 (아래 "사전 고정 규칙" 상수).
  결과를 본 뒤 규칙(유의수준, 문턱, 보호 변수 등)을 바꾸면 "백지에서 선별했다"는
  논리가 무너진다. 바꿔야 한다면 DSD를 돌리기 전에 바꾸고 그 사실을 기록할 것.

분석 방법 (Jones & Nachtsheim 2011/2017 의 DSD 분석을 따른다)
  응답 y (차압은 log, GPR과 동일) 마다 두 단계로 나눠 추정한다.

  ① 주효과 (홀수 성분)
     수준표 L(29×14)의 열은 서로 직교하므로 각 열의 주효과는 독립적으로 나온다:
         b_j = Σ L_rj · y_r / Σ L_rj²            (Σ L_rj² = 2(m−1) = 26)
     가짜 인자 3열의 b 는 실제 효과가 0인 열의 추정치 → 잡음·별칭의 크기.
         σ_b = sqrt( mean(b_fake²) )   (자유도 = 가짜 인자 수 3)
         t_j = b_j / σ_b,  p_j = 양측 t-검정 (df=3)

  ② 2차 효과·곡률 (짝수 성분)
     거울상 쌍의 평균 ȳ_i = (y_i + y_{i+m})/2 (14개) 와 중심점 1개, 총 15개 값에
         ȳ = c_0 + Σ_j c_j · L_ij²       (실제 변수 11개)
     를 최소제곱으로 맞춘다(자유도 15 − 12 = 3). c_j 가 변수 j 의 휘어짐(중간값 대비
     양 끝 평균의 차)이다. 2변수 상호작용도 이 짝수 성분에 섞이므로 c_j 는 "곡률 +
     관련 상호작용"의 신호로 해석한다 — 선별 목적엔 충분하다.

  ③ 효과 크기 — 분산 기여율 (Sobol 지수와 같은 눈금)
     f_main = b_j² · Var(L_j) / S_y²         (Var(L_j) = 26/29, 주효과가 설명하는 분산 비율)
     f_quad = c_j² · Var(L_j²) / S_y²        (Var(L_j²) = p(1−p), p = 26/29)
     S_y = 29회 응답의 표준편차.  참고용으로 E_j = |2·b_j| + |c_j| (응답 단위)도 같이 기록한다.

사전 고정 규칙 (변수 j 를 "영향 없음"으로 판정하는 조건)
  효과 성분(주효과, 곡률)은 아래 두 조건을 **모두** 만족할 때만 "있다"고 인정한다.
    (a) 통계적으로 구분됨 : p ≤ ALPHA            (가짜 인자 바닥과 구분되는가)
    (b) 실무적으로 의미 있음 : 분산 기여율 ≥ SHARE_MIN   (응답 변동의 2% 이상을 설명하는가)
  모든 응답에서 두 성분 모두 인정되지 않으면 그 변수는 영향 없음.

  두 조건이 다 필요한 이유 (스모크 테스트에서 확인)
    · (a)만 쓰면: 결정론적 CFD는 잡음이 거의 없어 각도가 중량을 10 g 바꾸는 수준도 "유의"하다.
    · (b)만 쓰면: DSD 곡률 성분에는 강한 변수들의 2변수 상호작용이 섞여, 둔감한 변수의
      곡률 추정치가 크게 부풀 수 있다(유의하지 않은데도). 유의성으로 걸러야 한다.
  SHARE_MIN = 0.02 는 V5 216점 Sobol 분석에서 둔감 변수를 판정한 기준(총효과 ≤ 0.02)과 같은 값.

  영향 없음 판정 변수 중 PROTECTED 에 없는 것을 고정한다(MAX_DROP 이 정해져 있으면
  분산 기여율 최댓값이 작은 순으로 그 개수까지만).

고정값 규칙 (사전 고정)
  "열성능에 무관한 변수는 중량이 최소가 되는 수준으로 고정"
    중량 모델 ŵ(ℓ) = b_w·ℓ + c_w·ℓ² 을 ℓ ∈ {−1, 0, +1} 에서 비교해 최소인 수준을 고른다.
    단 그 변수가 중량에서도 영향 없음(위 규칙)이면 FALLBACK_LEVEL.
  고정은 단위 좌표 u = (ℓ+1)/2 로 기록한다(핀 개수처럼 두께에 따라 범위가 바뀌는 변수도
  항상 만들 수 있는 형상이 되도록 — params.py 참고).
"""
import json
import os
import time

import numpy as np
import pandas as pd
from scipy import stats

from DSD import COLUMN_ORDER, FAKE_NAMES, M, N_RUNS, N_FAKE, get_plan
from params import CANDIDATES, N_CAND_DIM, decode
from responses import MODELED_NAMES, LOG_RESP, UNIT
from paths import DSD_RESULTS_PATH, DSD_EFFECTS_PATH, SCREENING_PATH

# ══════════════ 사전 고정 규칙 — DSD 실행 전에 확정할 것 ══════════════
ALPHA          = 0.10    # 유의수준 (선별 단계라 0.05보다 느슨하게 — 중요한 변수를 놓치지 않는 쪽)
SHARE_MIN      = 0.02    # 실무 문턱 = 응답 분산의 2% (V5 Sobol 둔감 판정 기준과 동일)
PROTECTED      = ()      # 판정과 무관하게 항상 남길 변수 (예: ("input_thick",)) — 실험 전에만 수정
MAX_DROP       = None    # 고정할 최대 개수 (None = 영향 없음 판정 변수 전부)
FALLBACK_LEVEL = 0       # 중량으로도 구분이 안 될 때 고정 수준 (0 = 범위 중앙)
# ═══════════════════════════════════════════════════════════════════════

REAL_IDX = [COLUMN_ORDER.index(n) for n in CANDIDATES]
FAKE_IDX = [COLUMN_ORDER.index(n) for n in FAKE_NAMES]


def load_dsd_data():
    """실험표 + 결과를 run 기준으로 합친다. 29회가 다 없으면 무엇이 빠졌는지 알려주고 중단."""
    plan = get_plan()
    if not os.path.exists(DSD_RESULTS_PATH):
        raise FileNotFoundError(f"DSD 결과 파일이 없음: {DSD_RESULTS_PATH}")
    res = pd.read_csv(DSD_RESULTS_PATH)
    missing = sorted(set(plan["run"]) - set(res["run"]))
    if missing:
        raise RuntimeError(
            f"DSD {N_RUNS}회 중 {len(missing)}회가 없음: run {missing}\n"
            "  DSD는 직교 구조라 한 회라도 빠지면 분석할 수 없다 — main.py 로 빠진 run 을 다시 돌릴 것\n"
            "  (failed_dsd.csv 에 기록된 run 은 ML.retry_failed_dsd() 로 재시도 목록에 다시 올릴 수 있음)")
    res = res.drop_duplicates("run", keep="last").set_index("run").loc[plan["run"]]
    L = plan[[f"c_{n}" for n in COLUMN_ORDER]].values.astype(float)
    return plan, res.reset_index(), L


def analyze_response(L, y):
    """응답 하나에 대한 주효과·곡률 추정과 검정. 변수(실제+가짜)별 dict 목록 반환."""
    n = len(y)
    assert n == N_RUNS and L.shape == (N_RUNS, M)
    S = float(np.std(y))
    var_x = float(np.mean(L[:, 0] ** 2))            # 26/29 (모든 열 동일)
    var_x2 = var_x * (1 - var_x)                    # Var(L²), L² 는 0/1

    # ① 주효과
    ss = (L ** 2).sum(axis=0)                     # = 2(m−1)
    b = (L * (y - y.mean())[:, None]).sum(axis=0) / ss
    sigma_b = float(np.sqrt(np.mean(b[FAKE_IDX] ** 2)))
    t_main = b / max(sigma_b, 1e-300)
    p_main = 2 * stats.t.sf(np.abs(t_main), df=N_FAKE)

    # ② 곡률 (짝수 성분)
    ye = np.concatenate([(y[:M] + y[M:2 * M]) / 2.0, [y[2 * M]]])
    Q = np.column_stack([np.ones(M + 1),
                         np.vstack([L[:M, REAL_IDX] ** 2, np.zeros((1, N_CAND_DIM))])])
    coef, *_ = np.linalg.lstsq(Q, ye, rcond=None)
    df_e = (M + 1) - Q.shape[1]
    resid = ye - Q @ coef
    s2 = float(resid @ resid) / df_e if df_e > 0 else np.nan
    cov = s2 * np.linalg.pinv(Q.T @ Q)
    c = coef[1:]
    se_c = np.sqrt(np.maximum(np.diag(cov)[1:], 1e-300))
    t_quad = c / se_c
    p_quad = 2 * stats.t.sf(np.abs(t_quad), df=df_e) if df_e > 0 else np.full(N_CAND_DIM, np.nan)

    out = []
    for j, name in enumerate(COLUMN_ORDER):
        is_fake = name in FAKE_NAMES
        jr = None if is_fake else CANDIDATES.index(name)
        cj = 0.0 if is_fake else float(c[jr])
        E = abs(2 * b[j]) + abs(cj)
        S2 = S * S if S > 0 else np.inf
        out.append({
            "variable": name, "fake": is_fake,
            "b_main": float(b[j]), "t_main": float(t_main[j]), "p_main": float(p_main[j]),
            "c_quad": cj,
            "t_quad": np.nan if is_fake else float(t_quad[jr]),
            "p_quad": np.nan if is_fake else float(p_quad[jr]),
            "f_main": float(b[j] ** 2 * var_x / S2),
            "f_quad": float(cj ** 2 * var_x2 / S2),
            "E": float(E), "E_over_S": float(E / S) if S > 0 else np.nan, "S": S,
        })
    return out


def _inactive(row):
    main_on = row["p_main"] <= ALPHA and row["f_main"] >= SHARE_MIN
    quad_on = (not np.isnan(row["p_quad"])) and row["p_quad"] <= ALPHA and row["f_quad"] >= SHARE_MIN
    return not (main_on or quad_on)


def run_analysis(write=True, verbose=True):
    plan, res, L = load_dsd_data()

    rows = []
    for resp in MODELED_NAMES:
        y = res[resp].values.astype(float)
        if LOG_RESP[resp]:
            y = np.log(y)
        for r in analyze_response(L, y):
            r["response"] = resp
            r["inactive"] = _inactive(r)
            rows.append(r)
    eff = pd.DataFrame(rows)

    real = eff[~eff["fake"]]
    summary = (real.groupby("variable")
               .agg(all_inactive=("inactive", "all"),
                    max_share=("f_main", "max"), max_share_q=("f_quad", "max"))
               .reindex(CANDIDATES))
    summary["max_share"] = summary[["max_share", "max_share_q"]].max(axis=1)
    fake_floor = eff[eff["fake"]].groupby("response")["f_main"].max()

    cand_drop = [v for v in CANDIDATES if summary.loc[v, "all_inactive"] and v not in PROTECTED]
    cand_drop.sort(key=lambda v: summary.loc[v, "max_share"])
    dropped = cand_drop if MAX_DROP is None else cand_drop[:MAX_DROP]
    active = [v for v in CANDIDATES if v not in dropped]

    # 고정값: 중량 최소 수준
    w = eff[(eff["response"] == "weight")].set_index("variable")
    fixed_level, fixed_u, why = {}, {}, {}
    for v in dropped:
        bw = w.loc[v, "b_main"] if w.loc[v, "p_main"] <= ALPHA else 0.0
        cw = w.loc[v, "c_quad"] if w.loc[v, "p_quad"] <= ALPHA else 0.0
        levels = np.array([-1, 0, 1])
        wl = bw * levels + cw * levels ** 2
        if bw == 0.0 and cw == 0.0:
            lv, why[v] = FALLBACK_LEVEL, "중량 차이도 구분 불가 → 사전 지정 수준"
        else:
            lv, why[v] = int(levels[np.argmin(wl)]), "중량 최소 수준"
        fixed_level[v] = int(lv)
        fixed_u[v] = (lv + 1) / 2.0

    # 고정값의 실제 치수(활성 변수는 중앙일 때 기준 — 핀 개수만 두께에 따라 달라질 수 있음)
    u_rep = np.full(N_CAND_DIM, 0.5)
    for v, uv in fixed_u.items():
        u_rep[CANDIDATES.index(v)] = uv
    x_rep = decode(u_rep)
    fixed_values = {v: float(x_rep[CANDIDATES.index(v)]) for v in dropped}

    decision = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_runs": N_RUNS, "n_fake": N_FAKE,
        "rule": {"ALPHA": ALPHA, "SHARE_MIN": SHARE_MIN, "PROTECTED": list(PROTECTED),
                 "MAX_DROP": MAX_DROP, "FALLBACK_LEVEL": FALLBACK_LEVEL,
                 "fixed_value_rule": "min_weight"},
        "active": active,
        "dropped": dropped,
        "inactive_but_kept": [v for v in cand_drop if v not in dropped],
        "fixed_level": fixed_level,
        "fixed_u": fixed_u,
        "fixed_values_representative": fixed_values,
        "fixed_reason": why,
    }

    if write:
        os.makedirs(os.path.dirname(DSD_EFFECTS_PATH), exist_ok=True)
        eff.to_csv(DSD_EFFECTS_PATH, index=False)
        with open(SCREENING_PATH, "w", encoding="utf-8") as f:
            json.dump(decision, f, ensure_ascii=False, indent=2)

    if verbose:
        _report(eff, summary, fake_floor, decision)
    return eff, decision


def _p_cell(p, f):
    """p값 한 칸(9자). 성분이 인정되면 *, 아니면 ·"""
    if np.isnan(p):
        return f"{'-':>9s}"
    s = "<0.001" if p < 0.001 else f"{p:.3f}"
    return f"{s:>8s}{'*' if (p <= ALPHA and f >= SHARE_MIN) else '·'}"


def _report(eff, summary, fake_floor, decision):
    print(f"\n=== DSD 선별 결과 ({N_RUNS}회, 가짜 인자 {N_FAKE}개) ===")
    print(f"규칙: 효과 성분은 p ≤ {ALPHA} 이고 분산 기여율 ≥ {SHARE_MIN:.0%} 일 때만 인정 — 모든 응답에서 없으면 영향 없음\n")
    resp = MODELED_NAMES
    print(f"{'변수':>18s} | " + " ".join(f"{r[:9]:>9s}" for r in resp) + " | 판정")
    eff = eff.assign(share=eff[["f_main", "f_quad"]].max(axis=1))
    piv = eff.pivot(index="variable", columns="response", values="share")
    ina = eff.pivot(index="variable", columns="response", values="inactive")
    for v in CANDIDATES + FAKE_NAMES:
        cells = " ".join(f"{100*piv.loc[v, r]:7.1f}%{'·' if ina.loc[v, r] else '*'}" for r in resp)
        if v in FAKE_NAMES:
            tag = "(가짜 인자)"
        elif v in decision["dropped"]:
            tag = f"고정 → {decision['fixed_values_representative'][v]:g} ({decision['fixed_reason'][v]})"
        elif v in decision["inactive_but_kept"]:
            tag = "영향 없음이나 유지(MAX_DROP)"
        elif v in PROTECTED:
            tag = "유지(보호)"
        else:
            tag = "활성"
        print(f"{v:>18s} | {cells} | {tag}")
    print("\n  숫자 = 분산 기여율(주효과·곡률 중 큰 값),  * = 그 응답에서 영향 있음(p·기여율 둘 다 통과),  · = 영향 없음")

    # 성분별 p값 — * 는 그 성분이 p ≤ ALPHA 이고 기여율 ≥ SHARE_MIN 인 경우
    for comp, title in (("main", "주효과 p"), ("quad", "곡률 p")):
        pp = eff.pivot(index="variable", columns="response", values=f"p_{comp}")
        ff = eff.pivot(index="variable", columns="response", values=f"f_{comp}")
        print(f"\n[{title}]")
        print(f"{'변수':>18s} | " + " ".join(f"{r[:9]:>9s}" for r in resp))
        for v in CANDIDATES + FAKE_NAMES:
            cells = " ".join(_p_cell(pp.loc[v, r], ff.loc[v, r]) for r in resp)
            print(f"{v:>18s} | {cells}")
    print(f"\n  숫자 = p값,  * = 그 성분 인정(p ≤ {ALPHA} 이고 기여율 ≥ {SHARE_MIN:.0%}),"
          "  · = 불인정,  - = 추정 안 함(가짜 인자 곡률)")
    print(f"\n2단계 활성 변수 {len(decision['active'])}개: {decision['active']}")
    print(f"고정 변수 {len(decision['dropped'])}개: {decision['dropped']}")


if __name__ == "__main__":
    run_analysis()
