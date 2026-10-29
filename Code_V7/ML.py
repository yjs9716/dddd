"""
V7 캠페인 관리 — 1단계 DSD 진행 기록 + 2단계 GPR 대체모델 · IMSE 적응샘플링 · 자동종료 (V6 ML.py 기반)

캠페인 단계 (campaign_state)
  "dsd"            : DSD 37회 진행 중 — dsd_plan.csv 의 run 을 순서대로 제안
  "need_screening" : DSD 완료, screening_decision.json 없음
                     → main.py 가 DSD_analysis 를 자동 실행해 넘어간다(main.AUTO_SCREENING, 사전 고정 규칙)
  "olhd"           : 2단계 진행 중 — DOE(10×활성 변수 수) → IMSE 적응샘플링
  "done"           : 종료기준 충족

종료기준 (V6 데이터로 정한 최종 로직 — √IMSE 포화)
  U_j(n) = √( 고정 후보점 N_U_CAND 개에서 σ_j(x)² 의 평균 ) ÷ S_j
      σ_j : 목적함수 j 의 GPR 예측 표준편차에서 CFD 노이즈(WhiteKernel)를 뺀 값. log 학습 지표는 예측값을 곱해 원 단위
  r_j(n) = ( U_j(n − STOP_WINDOW) − U_j(n) ) ÷ U_j(n − STOP_WINDOW)      (20회 전 대비 감소율)
  4개 목적함수 모두 r_j < STOP_RATE 인 상태가 STOP_CONSECUTIVE 회 연속이면 종료.
  매 회차 U_j·r_j 를 u_history.csv 에 남긴다. 다음 실험점 선정은 STOP_RATE 와 무관하므로, STOP_RATE 를 작게(1%)
  두고 길게 돌린 뒤 u_history 에서 5% 를 처음 만족한 시점 n* 을 사후에 찾아도 처음부터 5% 로 돌린 것과 같다
  (n* 까지 = 최종 대리모델, 이후 점 = 독립 검증).
  점별 예측오차 |예측 − 실측| ÷ (α·S_j) 는 err_* 열에 계속 기록한다(보고용, 종료 판정에는 안 씀).

V6 에서 그대로 가져온 것
  · 적응샘플링: σ 상위 후보 → IMSE 최대. 4개 목적함수를 항상 같이 고려한다(V6 의 "수렴한 목적함수 제외"는 뺐다)
  · GPR: Const × Matern(ν=2.5, ARD) + White, normalize_y, 차압만 log
  · 하이퍼파라미터 5회 재사용 + joblib 병렬
  · 입력은 선별 후 활성 변수(params.Screening), 결과 CSV에는 후보 전부(고정 변수는 상수 열)
  · DSD 실험표·실패 재시도 (1단계)

V7 에서 바뀐 것
  · 목적함수가 차압 · 채널 간 온도편차 · 최고온도 · 채널 안 온도편차(responses.py)라 종료 판정도 이 넷으로 한다.
  · 후보에 유량·유로 깊이가 들어가 DSD 를 V7 조건(후보 13개, 37회)으로 다시 한다.
  · S_j 는 "유량 효과를 뺀 설계끼리의 흩어짐"으로 정한다(_get_S_j). 유량은 운전 조건이라 차압(∝ 유량)과
    온도(∝ 1/유량) 흩어짐의 대부분을 차지하는데, 그대로 S_j 에 넣으면 기준(α·S_j)이 느슨해져 같은 유량에서
    설계끼리의 차이를 구분하기 전에 캠페인이 끝날 수 있다. DOE 응답에서 유량에 대한 2차 다항식 추세를 빼고
    남은 값의 표준편차를 S_j 로 쓴다(유량이 활성 변수일 때만).
"""
import json
import os
import time

import numpy as np
import pandas as pd
from scipy.stats import qmc
from joblib import Parallel, delayed

from params import CANDIDATES, OPERATING_PARAMS, Screening, to_dict
from fins import BANKS, bank_gap, all_banks_feasible
from responses import OBJ_NAMES, MODELED, MODELED_NAMES, RECORD_ONLY, UNIT
from paths import (DSD_RESULTS_PATH, DSD_FAILED_PATH, SCREENING_PATH,
                   RESULTS_PATH, FAILED_PATH)
import DSD

# ── 실험 설정 (V5와 동일) ──
N_CONSECUTIVE = 3        # (보고용) 점별 예측오차 연속 만족 횟수 — 종료 판정에는 안 씀
ALPHA = 0.1              # 점별 예측오차 정규화 α·S_j (err_* 열)

# ── 종료기준: √IMSE 포화 (모듈 설명) ──
STOP_WINDOW      = 20     # 감소율 비교 간격 [회]
STOP_RATE        = 0.01   # 논문 기준은 5% — 실험점 선정과 무관하므로 1% 로 길게 돌리고 5% 시점은 u_history 로 사후 판정
STOP_CONSECUTIVE = 3
N_U_CAND         = 4096   # U_j 를 계산하는 고정 후보점 (Sobol, seed U_SEED, decode 로 갭 제약 만족)
U_SEED           = 2026
U_HISTORY_PATH   = os.path.join(os.path.dirname(RESULTS_PATH), "u_history.csv")

N_CAND        = 65536
N_IMSE_CAND   = 2000
N_IMSE_REF    = 1024
MIN_DIST_NORM = 0.05

GAP_COLS = [f"fin_gap_{b}" for b in BANKS]
_METRIC_COLS = [c for n in MODELED_NAMES for c in (f"pred_{n}", n, f"err_{n}")]
_COLUMNS = ["idx"] + CANDIDATES + GAP_COLS + _METRIC_COLS + RECORD_ONLY
_DSD_COLUMNS = ["run"] + CANDIDATES + GAP_COLS + MODELED_NAMES + RECORD_ONLY

TERMINATION_GROUPS = {n: {"members": [n]} for n in OBJ_NAMES}
GROUP_NAMES = list(TERMINATION_GROUPS)
GROUP_UNIT = {g: " " + UNIT[g] for g in GROUP_NAMES}


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
    """임시 파일에 쓴 뒤 바꿔치기 — 쓰는 도중 프로세스가 강제 종료돼도 기존 파일이 깨지지 않는다."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = [c for c in columns if c in df.columns]
    extras = [c for c in df.columns if c not in columns]
    tmp = path + ".tmp"
    df[ordered + extras].to_csv(tmp, index=False)
    os.replace(tmp, path)


# ── 지금 해석 중인 점 (무인 운전용, run_forever.py) ──
#   main.py 가 실험 하나를 시작할 때 적고, 결과든 실패든 기록을 마치면 지운다. 프로세스가 도중에 죽거나
#   멈춰서 강제 종료되면 이 파일이 남으므로, run_forever.py 가 그 점을 실패로 기록한다
#   → MAX_FAIL_PER_POINT 규칙으로 같은 점에서 계속 죽는 경우 건너뛴다.
def _running_path():
    return os.path.join(os.path.dirname(RESULTS_PATH), "running_job.json")


def mark_running(phase, idx, params):
    path = _running_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"phase": phase, "idx": idx, "params": params,
                   "start": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False, default=float)
    os.replace(path + ".tmp", path)


def load_running():
    path = _running_path()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clear_running():
    if os.path.exists(_running_path()):
        os.remove(_running_path())


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
           **{n: results[n] for n in MODELED_NAMES},
           **{n: results.get(n, np.nan) for n in RECORD_ONLY}}
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
        attempt = _n_matches(df, [params[n] for n in CANDIDATES]) + 1
        row = {**_row_params(params), "reason": str(reason)[:300],
               "time": time.strftime("%Y-%m-%d %H:%M:%S"), "attempt": attempt}
        path, cols = FAILED_PATH, _FAILED_COLUMNS
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
        from OLHD import get_olhd_plan
        _DOE_SAMPLES = get_olhd_plan(screening())
    return _DOE_SAMPLES


def _load_results():
    return _read(RESULTS_PATH, _COLUMNS)


# 실패 기록은 지우지 않고 이력으로 쌓는다(시각·몇 번째 시도). DOE 점은 실패 횟수가 이 값보다 적으면
# 다음 실험으로 다시 돌린다 — 통신 오류 같은 일시적 실패는 재실행으로 살리고, 형상 자체가 안 되는
# 점이 무한 반복되지 않게 막는다.
MAX_FAIL_PER_POINT = 2
_FAILED_COLUMNS = CANDIDATES + ["reason", "time", "attempt"]


def _load_failed():
    return _read(FAILED_PATH, _FAILED_COLUMNS)


def _n_matches(df, x):
    """기록(df)에서 설계값이 x(후보 13개, CANDIDATES 순서)와 같은 행 수."""
    if not len(df):
        return 0
    X = df[CANDIDATES].values.astype(float)
    return int(np.all(np.isclose(X, np.asarray(x, dtype=float), rtol=0, atol=1e-6), axis=1).sum())


def current_idx():
    return len(_load_results())


# ── DOE 점 판별 — 행 번호(idx)가 아니라 "설계값이 OLHD 실험계획에 있는가"로 가른다 ──
#   실패한 DOE 점이 영구히 빠지면 행 번호가 당겨져, idx < N 으로 가르면 첫 적응샘플링 점이 DOE 로 분류된다
#   (예측오차 미기록, S_j 에 섞임). 설계값 대조는 실패·재실행 순서와 무관하다.
def _plan_vectors():
    """OLHD 실험계획 N점의 설계값 (N, 13) — 기록에 저장되는 값과 같은 형태(to_dict, 핀 개수 정수)."""
    return np.array([[to_dict(r)[n] for n in CANDIDATES] for r in _get_doe_samples()], dtype=float)


def _in_plan_mask(df):
    """기록(df) 각 행이 OLHD 실험계획의 점인지 (bool 배열)."""
    if not len(df):
        return np.zeros(0, dtype=bool)
    X = df[CANDIDATES].values.astype(float)
    P = _plan_vectors()
    return np.array([np.any(np.all(np.isclose(P, x, rtol=0, atol=1e-6), axis=1)) for x in X])


def _is_plan_point(params):
    x = np.array([params[n] for n in CANDIDATES], dtype=float)
    return bool(np.any(np.all(np.isclose(_plan_vectors(), x, rtol=0, atol=1e-6), axis=1)))


def _next_doe(df, failed):
    """아직 성공하지 못했고 실패가 MAX_FAIL_PER_POINT 회 미만인 첫 DOE 점 → (k, params, 실패 횟수). 없으면 None."""
    for k, xv in enumerate(_plan_vectors()):
        if _n_matches(df, xv):
            continue
        n_fail = _n_matches(failed, xv)
        if n_fail >= MAX_FAIL_PER_POINT:
            continue
        return k, to_dict(xv), n_fail
    return None


def _olhd_next():
    """DOE 실험점 중 아직 성공하지 못했고 실패가 MAX_FAIL_PER_POINT 회 미만인 첫 점. 없으면 적응샘플링.
    순서 대신 설계값으로 성공·실패를 대조하므로, 실패한 점을 나중에 다시 돌려도 중복·건너뜀이 없다."""
    df = _load_results()
    nxt = _next_doe(df, _load_failed())
    if nxt is not None:
        k, x, n_fail = nxt
        retry = f"  (재실행 — 앞선 실패 {n_fail}회)" if n_fail else ""
        print(f"[DOE {k+1}/{n_doe()}]{retry} " + _fmt(x))
        return len(df), x
    params = _gpr_suggest(df)
    print(f"[적응샘플링 {int((~_in_plan_mask(df)).sum()) + 1}회차] " + _fmt(params))
    return len(df), params


def _design_spread(doe_rows, name):
    """DOE 응답의 설계공간 표준편차. 유량(운전 조건)이 활성 변수면 유량에 대한 2차 다항식 추세를 빼고 남은 값의
    표준편차 — "같은 유량에서 설계끼리 얼마나 다른가" (모듈 설명)."""
    y = doe_rows[name].values.astype(float)
    ops = [n for n in OPERATING_PARAMS if n in screening().active]
    if not ops:
        return float(np.std(y))
    Q = np.column_stack([np.ones(len(y))] + [doe_rows[n].values.astype(float) ** k for n in ops for k in (1, 2)])
    coef, *_ = np.linalg.lstsq(Q, y, rcond=None)
    return float(np.std(y - Q @ coef))


def _get_S_j(df):
    """DOE 점들의 설계공간 표준편차 (종료 판정 기준). DOE 단계가 끝난 뒤(남은 DOE 점 없음)에만 정하고 고정한다."""
    global _S_J_CACHE
    if _S_J_CACHE:
        return _S_J_CACHE
    if _next_doe(df, _load_failed()) is not None:
        return None
    doe_rows = df[_in_plan_mask(df)]
    if len(doe_rows) < 2:
        return None
    _S_J_CACHE = {name: _design_spread(doe_rows, name) for name in OBJ_NAMES}
    ops = [n for n in OPERATING_PARAMS if n in screening().active]
    how = f" — {', '.join(ops)} 2차 추세를 뺀 값" if ops else ""
    print(f"\n[S_j 고정] DOE {len(doe_rows)}점 기준 설계공간 표준편차{how} (계획 {n_doe()}점):")
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
    adaptive = not _is_plan_point(params)      # DOE 점은 예측 없이 기록, 적응샘플링 점만 해석 전 예측과 비교
    if adaptive:
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
    row.update({n: results.get(n, np.nan) for n in RECORD_ONLY})
    row.update({f"pred_{n}": preds[n] for n in MODELED_NAMES})
    row.update({f"err_{n}": errs[n] for n in MODELED_NAMES})
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write(df, RESULTS_PATH, _COLUMNS)

    if adaptive:
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


_U_COLS = [f"U_{g}" for g in OBJ_NAMES]
_R_COLS = [f"r_{g}" for g in OBJ_NAMES]
_U_CAND = None


def _load_u_history():
    if os.path.exists(U_HISTORY_PATH):
        return pd.read_csv(U_HISTORY_PATH)
    return pd.DataFrame(columns=["n"] + _U_COLS + _R_COLS)


def is_done():
    """4개 목적함수 모두 r_j < STOP_RATE 인 상태가 STOP_CONSECUTIVE 회 연속 (모듈 설명)."""
    if not os.path.exists(SCREENING_PATH):
        return False
    hist = _load_u_history()
    if len(hist) < STOP_CONSECUTIVE:
        return False
    r = hist.sort_values("n").tail(STOP_CONSECUTIVE)[_R_COLS].values.astype(float)
    return bool(np.all(np.isfinite(r)) and np.all(r < STOP_RATE))


def _u_candidates():
    global _U_CAND
    if _U_CAND is None:
        sc = screening()
        u = qmc.Sobol(d=sc.n_dim, scramble=True, seed=U_SEED).random(N_U_CAND)
        _U_CAND = sc.normalize_active(sc.decode_active(u))
    return _U_CAND


def _latent_sigma(gpr, use_log, X):
    """GPR 예측 표준편차에서 CFD 노이즈(WhiteKernel) 몫을 뺀 값 — 원 단위(log 학습이면 예측값을 곱함)."""
    mu, sd = gpr.predict(X, return_std=True)
    y_std = float(np.ravel(getattr(gpr, "_y_train_std", 1.0))[0])
    noise = float(gpr.kernel_.k2.noise_level) * y_std ** 2
    sig = np.sqrt(np.maximum(sd ** 2 - noise, 0.0))
    return sig * np.exp(mu) if use_log else sig


def _record_u(models, n):
    """학습점 n 개 모델의 U_j(n) 과 20회 전 대비 감소율 r_j(n) 을 u_history.csv 에 기록."""
    s_j = _get_S_j(_load_results())
    if s_j is None:
        return
    X = _u_candidates()
    row = {"n": int(n)}
    for g in OBJ_NAMES:
        gpr, use_log = models[g]
        row[f"U_{g}"] = float(np.sqrt(np.mean(_latent_sigma(gpr, use_log, X) ** 2)) / s_j[g])
    hist = _load_u_history()
    hist = hist[hist["n"] != n]
    prev = hist[hist["n"] == n - STOP_WINDOW]
    for g in OBJ_NAMES:
        u0 = float(prev[f"U_{g}"].iloc[0]) if len(prev) else np.nan
        row[f"r_{g}"] = (u0 - row[f"U_{g}"]) / u0 if np.isfinite(u0) and u0 > 0 else np.nan
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True).sort_values("n")
    hist.to_csv(U_HISTORY_PATH, index=False)
    print(f"  [U_j, n={n}] " + "  ".join(f"{g} {row[f'U_{g}']:.4f}" + (f" (r {row[f'r_{g}']*100:+.1f}%)"
                                         if np.isfinite(row[f'r_{g}']) else "") for g in OBJ_NAMES))


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

    _record_u(models, len(df))                 # 종료 판정용 U_j(n) — 실험점 선정과는 무관
    active_objs = list(OBJ_NAMES)              # 4개 목적함수를 항상 같이 고려

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
    hist = _load_u_history()
    if len(hist):
        print(f"\n=== 종료 지표 U_j 와 {STOP_WINDOW}회 전 대비 감소율 r_j (종료: 모두 < {STOP_RATE:.0%} 가 "
              f"{STOP_CONSECUTIVE}회 연속) ===")
        print(hist.tail(10).to_string(index=False, float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    print("캠페인 상태:", campaign_state())
    if campaign_state() in ("dsd", "need_screening"):
        print("DSD 남은 run:", dsd_missing_runs())
        if campaign_state() == "need_screening":
            print("  DSD 완료 — main.py 를 실행하면 선별 판정을 자동으로 내린다(또는 `python DSD_analysis.py`)")
    else:
        report_progress()
