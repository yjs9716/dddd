"""
V6 캠페인 관리 — 1단계 DSD 진행 기록 + 2단계 GPR 대체모델 · IMSE 적응샘플링 · 자동종료

캠페인 단계 (campaign_state)
  "dsd"            : DSD 29회 진행 중 — dsd_plan.csv 의 run 을 순서대로 제안
  "need_screening" : DSD 29회 완료, screening_decision.json 없음
                     → DSD_analysis.py 를 실행해 선별 판정을 확정해야 다음으로 넘어감
                       (자동으로 넘어가지 않게 한 이유: 고정할 변수를 사람이 확인하고
                        SolidWorks 쪽 준비를 점검할 기회를 두기 위함. 판정 자체는 사전
                        고정 규칙으로 기계적으로 나오므로 결과를 바꿔서는 안 됨)
  "olhd"           : 2단계 진행 중 — DOE(10×활성 변수 수) → IMSE 적응샘플링
  "done"           : 종료기준 충족

V5(Code/ML.py)에서 그대로 가져온 것 (근거는 V5 주석에 상세)
  · 종료기준: |예측 − 실측| ≤ α·S_j (α=0.1, S_j는 DOE 점에서만 1회 계산 후 고정),
    모든 목적함수가 N_CONSECUTIVE회 연속 만족하면 종료
  · 적응샘플링: σ 상위 후보 → IMSE 최대
  · GPR: Const × Matern(ν=2.5, ARD) + White, normalize_y, 차압만 log
  · 하이퍼파라미터 5회 재사용 + joblib 병렬, 수렴한 목적함수는 샘플링 방향에서 제외

V5 대비 바뀐 것
  · GPR 입력 차원이 9로 고정이 아니라 선별 후 활성 변수 수(params.Screening).
  · 결과 CSV에는 후보 11개를 전부 기록한다(고정 변수는 상수 열) — 형상 재현용.
  · 후보점은 활성 변수 공간의 Sobol → Screening.decode_active (고정 변수 끼워 넣기 +
    뱅크별 핀 개수 접어 넣기)로 만든다.
"""
import os

import numpy as np
import pandas as pd
from scipy.stats import qmc
from joblib import Parallel, delayed

from params import CANDIDATES, Screening, to_dict
from fins import BANKS, bank_gap, all_banks_feasible
from responses import OBJECTIVES, OBJ_NAMES, MODELED, MODELED_NAMES
from paths import (DSD_RESULTS_PATH, DSD_FAILED_PATH, SCREENING_PATH,
                   RESULTS_PATH, FAILED_PATH)
import DSD

# ── 실험 설정 (V5와 동일) ──
N_CONSECUTIVE = 3
ALPHA = 0.1

N_CAND        = 65536
N_IMSE_CAND   = 2000
N_IMSE_REF    = 1024
MIN_DIST_NORM = 0.05

GAP_COLS = [f"fin_gap_{b}" for b in BANKS]
_METRIC_COLS = [c for n in MODELED_NAMES for c in (f"pred_{n}", n, f"err_{n}")]
_COLUMNS = ["idx"] + CANDIDATES + GAP_COLS + _METRIC_COLS
_DSD_COLUMNS = ["run"] + CANDIDATES + GAP_COLS + MODELED_NAMES

TERMINATION_GROUPS = {n: {"members": [n]} for n in OBJ_NAMES}
GROUP_NAMES = list(TERMINATION_GROUPS)
GROUP_UNIT = {"pressure_drop": " Pa", "temp_std": " °C", "max_temp": " °C",
              "std_pass1": " LPM", "std_pass2": " LPM"}


# ══════════════ 공통 I/O ══════════════
def _read(path, columns):
    if os.path.exists(path):
        df = pd.read_csv(path)
        for c in columns:
            if c not in df.columns:
                df[c] = np.nan
        return df
    return pd.DataFrame(columns=columns)


def _write(df, path, columns):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = [c for c in columns if c in df.columns]
    extras = [c for c in df.columns if c not in columns]
    df[ordered + extras].to_csv(path, index=False)


def _row_params(params):
    return {n: params[n] for n in CANDIDATES}


def _gaps(params):
    return {f"fin_gap_{b}": bank_gap(params, b) for b in BANKS}


# ══════════════ 1단계: DSD ══════════════
def _dsd_results():
    return _read(DSD_RESULTS_PATH, _DSD_COLUMNS)


def _dsd_failed():
    return _read(DSD_FAILED_PATH, ["run"] + CANDIDATES + ["reason"])


def dsd_pending_runs():
    """아직 성공하지 못했고, 실패 기록도 없는 run 목록 (순서대로)."""
    plan = DSD.get_plan()
    done = set(_dsd_results()["run"].dropna().astype(int))
    failed = set(_dsd_failed()["run"].dropna().astype(int))
    return [int(r) for r in plan["run"] if r not in done and r not in failed]


def dsd_missing_runs():
    plan = DSD.get_plan()
    done = set(_dsd_results()["run"].dropna().astype(int))
    return [int(r) for r in plan["run"] if r not in done]


def retry_failed_dsd():
    """실패 기록을 지워 해당 run 들을 다시 제안 목록에 올린다 (원인 수정 후 실행)."""
    if os.path.exists(DSD_FAILED_PATH):
        os.remove(DSD_FAILED_PATH)
    print(f"DSD 실패 기록 삭제 — 다시 시도할 run: {dsd_missing_runs()}")


def _dsd_params(run):
    plan = DSD.get_plan().set_index("run")
    row = plan.loc[run, CANDIDATES].values.astype(float)
    return to_dict(row)


def _record_dsd(run, params, results):
    df = _dsd_results()
    row = {"run": run, **_row_params(params), **_gaps(params),
           **{n: results[n] for n in MODELED_NAMES}}
    df = pd.concat([df[df["run"] != run], pd.DataFrame([row])], ignore_index=True)
    _write(df.sort_values("run"), DSD_RESULTS_PATH, _DSD_COLUMNS)
    print(f"[DSD run {run}] 결과 저장 ({len(df)}/{DSD.N_RUNS})")


# ══════════════ 캠페인 상태 / 외부 인터페이스 ══════════════
def campaign_state():
    if dsd_missing_runs():
        return "dsd"
    if not os.path.exists(SCREENING_PATH):
        return "need_screening"
    return "done" if is_done() else "olhd"


def next_job():
    """다음 실험 → (phase, idx, params).  더 할 게 없으면 (state, None, None)."""
    state = campaign_state()
    if state == "dsd":
        pend = dsd_pending_runs()
        if not pend:
            return "dsd_blocked", None, None     # 남은 run 이 전부 실패 기록 — 사람이 확인 필요
        run = pend[0]
        params = _dsd_params(run)
        print(f"[DSD {run+1}/{DSD.N_RUNS}] " + _fmt(params))
        return "dsd", run, params
    if state == "olhd":
        idx, params = _olhd_next()
        return "olhd", idx, params
    return state, None, None


def record(phase, idx, params, results):
    missing = [n for n in MODELED_NAMES if n not in results]
    if missing:
        raise KeyError(f"results 에 다음 값이 없음: {missing}")
    if phase == "dsd":
        _record_dsd(idx, params, results)
    else:
        _record_olhd(params, results)


def log_failure(phase, idx, params, reason):
    if phase == "dsd":
        df = _dsd_failed()
        row = {"run": idx, **_row_params(params), "reason": str(reason)[:300]}
        path, cols = DSD_FAILED_PATH, ["run"] + CANDIDATES + ["reason"]
    else:
        df = _load_failed()
        row = {**_row_params(params), "reason": str(reason)[:300]}
        path, cols = FAILED_PATH, CANDIDATES + ["reason"]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write(df, path, cols)
    print(f"  ⚠ [{phase}] 실패 기록 ({len(df)}건 누적): {reason}")


# ══════════════ 2단계: OLHD + 적응샘플링 ══════════════
_SC = None
_DOE_SAMPLES = None
_S_J_CACHE = {}
_KERNEL_CACHE = {}
_ROUNDS_SINCE_REFRESH = 10 ** 9
_REFRESH_EVERY = 5
_PENDING_PREDICTION = None


def screening():
    global _SC
    if _SC is None:
        _SC = Screening(SCREENING_PATH)
    return _SC


def n_doe():
    from OLHD import default_n_doe
    return default_n_doe(screening())


def _get_doe_samples():
    global _DOE_SAMPLES
    if _DOE_SAMPLES is None:
        from OLHD import generate_olhd
        _DOE_SAMPLES = generate_olhd(screening(), seed=42)
    return _DOE_SAMPLES


def _load_results():
    return _read(RESULTS_PATH, _COLUMNS)


def _load_failed():
    return _read(FAILED_PATH, CANDIDATES + ["reason"])


def current_idx():
    return len(_load_results())


def _olhd_next():
    df = _load_results()
    cursor = len(df) + len(_load_failed())
    N = n_doe()
    if cursor < N:
        params = to_dict(_get_doe_samples()[cursor])
        print(f"[DOE {cursor+1}/{N}] " + _fmt(params))
    else:
        params = _gpr_suggest(df)
        print(f"[적응샘플링 {cursor-N+1}회차] " + _fmt(params))
    return len(df), params


def _get_S_j(df):
    global _S_J_CACHE
    if _S_J_CACHE:
        return _S_J_CACHE
    N = n_doe()
    doe_rows = df[df["idx"] < N]
    if len(doe_rows) < N:
        return None
    _S_J_CACHE = {name: float(doe_rows[name].std(ddof=0)) for name in OBJ_NAMES}
    print(f"\n[S_j 고정] DOE {N}점 기준 설계공간 표준편차:")
    for name, s in _S_J_CACHE.items():
        print(f"    {name:16s} S_j={s:.5f}  threshold={ALPHA*s:.5f}")
    return _S_J_CACHE


def _thresholds():
    s_j = _get_S_j(_load_results())
    if s_j is None:
        return None
    return {g: ALPHA * s_j[g] for g in GROUP_NAMES}


def _record_olhd(params, results):
    global _PENDING_PREDICTION
    df = _load_results()
    idx = len(df)
    preds = {n: np.nan for n in MODELED_NAMES}
    errs = {n: np.nan for n in MODELED_NAMES}
    if idx >= n_doe():
        cached = _PENDING_PREDICTION
        if cached is not None and cached["idx"] == idx and cached["params"] == params:
            preds = cached["preds"]
        else:
            print("  (참고: 예측 캐시 불일치 — 새로 계산)")
            preds = _predict_point(df, params)
        _PENDING_PREDICTION = None
        thr = _thresholds()
        for name in MODELED_NAMES:
            abs_err = abs(preds[name] - results[name])
            if name in TERMINATION_GROUPS and thr is not None:
                errs[name] = abs_err / thr[name]
            else:
                errs[name] = abs_err / abs(results[name]) * 100

    row = {"idx": idx, **_row_params(params), **_gaps(params)}
    row.update({n: results[n] for n in MODELED_NAMES})
    row.update({f"pred_{n}": preds[n] for n in MODELED_NAMES})
    row.update({f"err_{n}": errs[n] for n in MODELED_NAMES})
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write(df, RESULTS_PATH, _COLUMNS)

    if idx >= n_doe():
        g = _group_values(df.tail(1))
        print(f"[{idx}] 예측오차(절대): " + "  ".join(f"{k} {g[k][0]:.4f}{GROUP_UNIT[k]}" for k in GROUP_NAMES))
    print(f"[{idx}] 결과 저장 완료")


def _group_values(rows):
    out = {}
    for g in GROUP_NAMES:
        if f"pred_{g}" in rows.columns:
            out[g] = (rows[f"pred_{g}"] - rows[g]).abs().values.astype(float)
        else:
            out[g] = np.full(len(rows), np.nan)
    return out


def _group_ok(rows):
    thr = _thresholds()
    gv = _group_values(rows)
    if thr is None:
        return {g: np.zeros(len(rows), dtype=bool) for g in GROUP_NAMES}
    return {g: (gv[g] <= thr[g]) for g in GROUP_NAMES}


def _adaptive_rows(df):
    return df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])


def is_done():
    if not os.path.exists(SCREENING_PATH):
        return False
    adaptive = _adaptive_rows(_load_results())
    if len(adaptive) < N_CONSECUTIVE:
        return False
    ok = _group_ok(adaptive.tail(N_CONSECUTIVE))
    return bool(np.all([ok[g].all() for g in GROUP_NAMES]))


def _converged_objectives(df):
    adaptive = _adaptive_rows(df)
    if len(adaptive) < N_CONSECUTIVE:
        return set()
    ok = _group_ok(adaptive.tail(N_CONSECUTIVE))
    return {g for g in GROUP_NAMES if ok[g].all()}


# ── GPR ──
def _fit_gpr(Xs, y, n_dim, n_restarts=3, warm_kernel=None):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
    if warm_kernel is not None:
        gpr = GaussianProcessRegressor(kernel=warm_kernel, optimizer=None, normalize_y=True)
        return gpr.fit(Xs, y)
    kernel = (ConstantKernel(1.0, (1e-3, 1e3))
              * Matern(nu=2.5, length_scale=[0.3] * n_dim, length_scale_bounds=(0.05, 50.0))
              + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0)))
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts, normalize_y=True)
    return gpr.fit(Xs, y)


def _fit_models(df, use_cache=False):
    global _ROUNDS_SINCE_REFRESH
    sc = screening()
    Xs = sc.normalize_active(df[CANDIDATES].values.astype(float))
    refresh = (not use_cache) or (not _KERNEL_CACHE) or (_ROUNDS_SINCE_REFRESH >= _REFRESH_EVERY)
    if use_cache:
        _ROUNDS_SINCE_REFRESH = 0 if refresh else _ROUNDS_SINCE_REFRESH + 1

    def _one(name, use_log):
        y = df[name].values.astype(float)
        y = np.log(y) if use_log else y
        warm = None if refresh else _KERNEL_CACHE.get(name)
        return name, _fit_gpr(Xs, y, sc.n_dim, warm_kernel=warm), use_log

    fitted = Parallel(n_jobs=-1)(delayed(_one)(n, lg) for n, lg in MODELED)
    models = {}
    for name, gpr, use_log in fitted:
        models[name] = (gpr, use_log)
        if use_cache and refresh:
            _KERNEL_CACHE[name] = gpr.kernel_
    return models


def _predict_point(df, params):
    models = _fit_models(df)
    xs = screening().normalize_active([[params[n] for n in CANDIDATES]])
    out = {}
    for name, (gpr, use_log) in models.items():
        v = float(gpr.predict(xs)[0])
        out[name] = float(np.exp(v)) if use_log else v
    return out


def _imse_reduction(gpr, cand, ref):
    from scipy.linalg import cho_solve
    k1 = gpr.kernel_.k1
    Xt = gpr.X_train_
    Kxc = k1(Xt, cand)
    A = cho_solve((gpr.L_, True), Kxc)
    chat = k1(ref, cand) - k1(Xt, ref).T @ A
    vC = k1.diag(cand) - np.einsum("ij,ij->j", Kxc, A)
    return (chat ** 2).mean(axis=0) / np.maximum(vC, 1e-12)


def _make_candidates(n_done):
    sc = screening()
    u = qmc.Sobol(d=sc.n_dim, scramble=True, seed=n_done).random(N_CAND)
    real = np.unique(sc.decode_active(u), axis=0)
    return real, sc.normalize_active(real)


def _gpr_suggest(df):
    global _PENDING_PREDICTION
    sc = screening()
    models = _fit_models(df, use_cache=True)
    cand_real, cand_norm = _make_candidates(len(df))

    done = [df[CANDIDATES].values.astype(float)]
    failed = _load_failed()
    if len(failed):
        done.append(failed[CANDIDATES].values.astype(float))
    done_norm = sc.normalize_active(np.vstack(done))
    from scipy.spatial.distance import cdist
    keep = cdist(cand_norm, done_norm).min(axis=1) >= MIN_DIST_NORM
    if keep.sum() == 0:
        print("  ⚠ 모든 후보가 기존 실험점과 근접 — 거리 제약 해제")
        keep[:] = True
    cand_real, cand_norm = cand_real[keep], cand_norm[keep]

    converged = _converged_objectives(df)
    active_objs = [n for n in OBJ_NAMES if n not in converged] or list(OBJ_NAMES)
    if converged:
        print(f"  (수렴 판단되어 다음 실험점 선정에서 제외: {sorted(converged)})")

    sig_sum = np.zeros(len(cand_norm))
    for name in active_objs:
        _, sig = models[name][0].predict(cand_norm, return_std=True)
        sig_sum += sig / (sig.max() + 1e-12)
    n_keep = min(N_IMSE_CAND, len(cand_norm))
    top = np.argpartition(-sig_sum, n_keep - 1)[:n_keep]
    cand_top_real, cand_top_norm = cand_real[top], cand_norm[top]

    ref = qmc.Sobol(d=sc.n_dim, scramble=True, seed=len(df) + 99991).random(N_IMSE_REF)
    score = np.zeros(len(cand_top_norm))
    for name in active_objs:
        red = _imse_reduction(models[name][0], cand_top_norm, ref)
        score += red / (red.max() + 1e-12)

    best_i = int(np.argmax(score))
    params = to_dict(cand_top_real[best_i])
    if not all_banks_feasible(params):
        raise RuntimeError(f"갭 제약 위반 후보가 선택됨: {params}")

    xs_best = cand_top_norm[best_i].reshape(1, -1)
    preds = {}
    for name, (gpr, use_log) in models.items():
        v = float(gpr.predict(xs_best)[0])
        preds[name] = float(np.exp(v)) if use_log else v
    _PENDING_PREDICTION = {"idx": len(df), "params": dict(params), "preds": preds}
    return params


def _fmt(params):
    parts = [f"{k}={int(params[k])}" if k.startswith("fin_count") else f"{k}={params[k]:.1f}"
             for k in CANDIDATES]
    parts.append("(gap " + "/".join(f"{bank_gap(params, b):.3f}" for b in BANKS) + ")")
    return "  ".join(parts)


# ── 진단 ──
def report_progress():
    adaptive = _adaptive_rows(_load_results())
    if not len(adaptive):
        print("적응샘플링 데이터가 아직 없습니다.")
        return
    gv, ok, thr = _group_values(adaptive), _group_ok(adaptive), _thresholds()
    print(f"\n=== 적응샘플링 오차 추이 ({len(adaptive)}회차) ===")
    if thr:
        print("  기준: " + "  ".join(f"{g}<={thr[g]:.4f}{GROUP_UNIT[g]}" for g in GROUP_NAMES))
    for i in range(len(adaptive)):
        print(f"  {i+1:3d}회 " + "".join(f"{gv[g][i]:13.4f}{'o' if ok[g][i] else 'x':>2s}" for g in GROUP_NAMES))


if __name__ == "__main__":
    print("캠페인 상태:", campaign_state())
    if campaign_state() in ("dsd", "need_screening"):
        print("DSD 남은 run:", dsd_missing_runs())
    else:
        report_progress()
