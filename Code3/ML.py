"""
V4 유로 8변수 — GPR 대체모델 + IMSE 적응 샘플링 + 예측오차 기반 자동종료

V3(Code2/ML.py) 대비 변경점 — 두 가지. 둘 다 V3 데이터(139점) 실측 분석으로 결정함.

  ① 학습 대상: vel_cv_pass1/pass2 (2개) → 레인별 유량 (14개)
     CV = std(레인유량)/mean(레인유량) 인데, 좋은 설계일수록 레인 유량이 거의
     같아져서 분자가 "거의 같은 수들의 차이"가 된다. 그래서 원래 값의 작은 오차가
     CV에서는 크게 증폭된다 — 레인 유량을 1% 오차로 맞혀도:
         진짜 CV 2% → CV 오차 16.7%  /  CV 5% → 6.0%  /  CV 10% → 2.9%
     즉 CV를 1%로 맞히려면 레인 유량을 0.1%까지 맞혀야 하는데 CFD가 그 정밀도를
     못 준다. V2 364점·V3 139점을 돌리고도 1% 기준을 한 번도 못 넘은 진짜 이유.

     레인 유량 자체는 형상에 따라 매끄럽게 변하는 물리량이라 GPR이 잘 배우고,
     1% 기준이 현실적이다. CV는 예측된 레인 유량으로부터 계산해서 GA 입력과
     사람이 보는 지표로 계속 쓴다 — 지표가 없어지는 게 아니라, "무엇을 학습할지"만
     한 단계 아래로 내린 것. (V2→V3에서 max(cv1,cv2)를 쪼갠 것과 같은 논리)

  ② 적응샘플링: σ x sparsity → IMSE
     V3의 `score *= sparsity`는 코너 쏠림을 잡으려고 넣은 보정인데, σ와 sparsity가
     둘 다 "기존 점에서 멀수록 커지는 값"이라 곱하면 보정이 아니라 증폭이었다.
     V3 데이터로 실측한 결과(DOE 80점 기준, 다음 1점을 고르게 했을 때
     cornerness는 0.5=평범 / 1.0=완전 코너):
         σ만                    0.717 (경계 5/8차원)
         σ x sparsity (V3)      0.845 (경계 7/8차원)   ← 오히려 악화
         IMSE                   0.461 (경계 1/8차원)
     실제로 V3 적응샘플링 59점 중 96.6%가 8차원 중 5개 이상이 경계 10%에 박혔다
     (무작위면 0.9%). 그 코너점들은 정보 가치도 낮았다 — 같은 30점을 추가했을 때
     고르게 퍼진 점은 cv2를 18.7% 개선시킨 반면 코너점은 1.5%밖에 개선 못 시켰다.

     IMSE는 "이 점을 찍으면 설계공간 전체의 불확실도가 얼마나 줄어드는가"를 본다.
     코너 점은 자기 주변 좁은 영역만 개선하므로 자연스럽게 후순위가 된다.
     별도의 페널티 항이나 튜닝 상수가 필요 없다는 게 장점.

V3에서 그대로 가져온 것
  - 설계공간 랜덤(Sobol) 후보 샘플링, 중복 제외(MIN_DIST_NORM)
  - 목적함수별 σ 정규화 후 합산, 수렴한 목적함수는 합산에서 제외
  - 제약조건(power_module_flow, weight)도 GPR 학습 — GA 단계 필터용
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import qmc

from OLHD import generate_olhd, PARAM_NAMES, LO, HI, N_DIM, DEFAULT_N_DOE, to_dict
from paths import RESULTS_PATH, FAILED_PATH
from result_parser import LANE1_NAMES, LANE2_NAMES, LANE_NAMES, _cv_from_flows

# ── 실험 설정 ────────────────────────────────────────────────
N_DOE         = DEFAULT_N_DOE   # 초기 DOE 샘플 수 = 10 x 변수수 (8변수 → 80)
ERR_THRESHOLD = 1.0    # 종료 기준: 예측오차 [%]
                       #   V3까지는 이 값이 도달 불가능했지만(CV의 증폭 때문),
                       #   레인 유량은 정상적인 물리량이라 1%가 현실적인 목표임
N_CONSECUTIVE = 3      # 연속 만족 횟수 (모든 목적함수 그룹이 동시 만족해야 종료)

# ── 적응 샘플링 설정 ──────────────────────────────────────────
N_CAND        = 65536   # σ로 1차 선별할 후보점 수 (Sobol 균형성 위해 2^16)
N_IMSE_CAND   = 2000    # 그중 σ 상위 몇 개에 대해 IMSE를 계산할지
N_IMSE_REF    = 1024    # IMSE 적분에 쓸 참고점 수 (설계공간 전체에 흩뿌림)
MIN_DIST_NORM = 0.05    # 정규화 공간에서 기존 실험점과 이 거리 미만이면 후보 제외

# ── 목적함수 (17개 = 레인 14 + 차압 + 온도std + 최고온도) ──────
#    (이름, log변환 여부)
#    레인 유량에 log를 쓰지 않는 이유: 값의 범위가 좁고(총 4 LPM을 7개로 나눔)
#    0에 가까워지지 않으므로 선형 공간에서 충분히 잘 학습됨
OBJECTIVES = (
    [("pressure_drop", True)]                    # 차압은 스케일이 넓어 log
    + [("temp_std", False), ("max_temp", False)]
    + [(n, False) for n in LANE_NAMES]           # 레인 14개
)
OBJ_NAMES = [o[0] for o in OBJECTIVES]

# ── 제약조건용 지표 ────────────────────────────────────────────
#    GPR 학습 + 예측까지는 목적함수와 동일하게 하지만,
#    적응샘플링 방향과 종료판정에는 관여하지 않음.
CONSTRAINTS = [
    ("power_module_flow", False),
    ("weight",            False),
]
CONSTRAINT_NAMES = [c[0] for c in CONSTRAINTS]

MODELED       = OBJECTIVES + CONSTRAINTS
MODELED_NAMES = OBJ_NAMES + CONSTRAINT_NAMES

# ── 종료판정 그룹 ──────────────────────────────────────────────
#    레인 14개를 각각 독립 조건으로 걸면 "17개가 동시에 3연속"이 되어
#    조합이 기하급수적으로 어려워진다(0.9^51 수준). 레인은 같은 물리량이므로
#    통과별로 묶어서 "그 통과의 7개 레인 중 최대 오차"를 하나의 조건으로 본다.
#      → 종료 조건 5개: 차압 / 온도std / 최고온도 / 1차레인 / 2차레인
#    "최대"를 쓰는 이유: "레인 유량을 전부 1% 이내로 맞힌다"가 우리가 주장하려는
#    내용이므로, 평균이 아니라 최악을 기준으로 삼는 게 정직함.
TERMINATION_GROUPS = {
    "pressure_drop": ["pressure_drop"],
    "temp_std":      ["temp_std"],
    "max_temp":      ["max_temp"],
    "lane_pass1":    LANE1_NAMES,
    "lane_pass2":    LANE2_NAMES,
}
GROUP_NAMES = list(TERMINATION_GROUPS)

_DOE_SAMPLES = None   # 실제로 DOE 단계를 밟을 때만 계산 (lazy)


def _get_doe_samples():
    """generate_olhd()는 10만 개 후보를 뒤지는 계산이라(수 초 소요) lazy로 둠."""
    global _DOE_SAMPLES
    if _DOE_SAMPLES is None:
        _DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)
    return _DOE_SAMPLES


# 지표별로 [예측값, 실측값, 오차]를 나란히 묶어서 CSV 훑어보기 편하게 정렬
_METRIC_COLS = [c for n in MODELED_NAMES for c in (f"pred_{n}", n, f"err_{n}")]
# CV는 학습 대상이 아니지만 실측/예측 둘 다 기록해둠 — GA 입력이자 사람이 보는 지표라
#   pred_vel_cv_*는 "예측된 레인 유량 14개로 계산한 CV"
_CV_COLS = ["pred_vel_cv_pass1", "vel_cv_pass1", "err_vel_cv_pass1",
            "pred_vel_cv_pass2", "vel_cv_pass2", "err_vel_cv_pass2"]
_COLUMNS = ["idx"] + PARAM_NAMES + _METRIC_COLS + _CV_COLS


def _load_results():
    if os.path.exists(RESULTS_PATH):
        df = pd.read_csv(RESULTS_PATH)
        for c in _COLUMNS:
            if c not in df.columns:
                df[c] = np.nan
        return df
    return pd.DataFrame(columns=_COLUMNS)


def _save_results(df):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    # 컬럼 순서를 _COLUMNS 기준으로 고정. _COLUMNS에 없는 예전 스키마 컬럼은
    # 뒤에 그대로 붙여 데이터가 사라지지 않게 함
    ordered = [c for c in _COLUMNS if c in df.columns]
    extras  = [c for c in df.columns if c not in _COLUMNS]
    df[ordered + extras].to_csv(RESULTS_PATH, index=False)


def _load_failed():
    if os.path.exists(FAILED_PATH):
        return pd.read_csv(FAILED_PATH)
    return pd.DataFrame(columns=PARAM_NAMES + ["reason"])


def log_failure(params, reason):
    """리빌드/해석 실패한 실험점 기록 → 같은 점을 다시 제안하지 않도록."""
    df = _load_failed()
    row = dict(params)
    row["reason"] = str(reason)[:300]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(os.path.dirname(FAILED_PATH), exist_ok=True)
    df.to_csv(FAILED_PATH, index=False)
    print(f"  ⚠ 실패 기록 ({len(df)}건 누적): {reason}")


def _normalize(X):
    return (np.asarray(X, dtype=float) - LO) / (HI - LO)


def current_idx():
    """다음에 기록될 실험 번호 (= 지금까지 성공한 실험 수)."""
    return len(_load_results())


# ================== 외부 인터페이스 ==================
def get_next_params():
    """다음 실험할 파라미터 dict 반환 — {변수명: 값} 8개."""
    df       = _load_results()
    n_failed = len(_load_failed())
    # DOE 단계에서는 '시도한 횟수' 기준으로 진행해야 실패점에서 무한루프에 빠지지 않음
    doe_cursor = len(df) + n_failed

    if doe_cursor < N_DOE:
        params = to_dict(_get_doe_samples()[doe_cursor])
        print(f"[DOE {doe_cursor+1}/{N_DOE}] " + _fmt(params))
    else:
        params = _gpr_suggest(df)
        print(f"[적응샘플링 {doe_cursor-N_DOE+1}회차] " + _fmt(params))

    return params


def update_ml(params, results):
    """
    해석 결과 저장. 적응 단계면 '이번 실험 데이터가 들어가기 전 모델의 예측값'도 함께 기록.
      params  : {변수명: 값} 8개
      results : {값 이름: 실측값} — MODELED_NAMES가 전부 있어야 함
                (vel_cv_pass1/2 등 참고용 값이 더 있어도 무방)
    """
    df  = _load_results()
    idx = len(df)

    missing = [n for n in MODELED_NAMES if n not in results]
    if missing:
        raise KeyError(f"update_ml에 넘긴 results에 다음 값이 없음: {missing}")

    preds = {n: np.nan for n in MODELED_NAMES}
    errs  = {n: np.nan for n in MODELED_NAMES}
    cv_pred = {}
    if idx >= N_DOE:
        preds = _predict_point(df, params)
        for name in MODELED_NAMES:
            errs[name] = abs(preds[name] - results[name]) / abs(results[name]) * 100

        # 예측된 레인 유량으로부터 CV를 계산 — 실측 CV와 같은 식(_cv_from_flows)을 씀
        cv_pred["pred_vel_cv_pass1"] = _cv_from_flows([preds[n] for n in LANE1_NAMES])
        cv_pred["pred_vel_cv_pass2"] = _cv_from_flows([preds[n] for n in LANE2_NAMES])

        g = _group_errors(errs)
        msg = [f"{k} {g[k]:.2f}%" for k in GROUP_NAMES]
        print(f"[{idx}] 예측오차: " + "  ".join(msg)
              + f"  (종료기준: 전부 {ERR_THRESHOLD}% 이하 {N_CONSECUTIVE}회 연속)")
        if "vel_cv_pass1" in results:
            print(f"      CV 참고 — 1차 예측 {cv_pred['pred_vel_cv_pass1']:.2f}% / "
                  f"실측 {results['vel_cv_pass1']:.2f}%,  "
                  f"2차 예측 {cv_pred['pred_vel_cv_pass2']:.2f}% / "
                  f"실측 {results['vel_cv_pass2']:.2f}%")

    row = {"idx": idx}
    row.update(params)
    row.update({n: results[n] for n in MODELED_NAMES})
    row.update({f"pred_{n}": preds[n] for n in MODELED_NAMES})
    row.update({f"err_{n}": errs[n] for n in MODELED_NAMES})

    # CV(학습 대상 아님) 기록 — 실측은 항상, 예측은 적응 단계에서만
    for pass_no in (1, 2):
        meas = results.get(f"vel_cv_pass{pass_no}", np.nan)
        pred = cv_pred.get(f"pred_vel_cv_pass{pass_no}", np.nan)
        row[f"vel_cv_pass{pass_no}"]      = meas
        row[f"pred_vel_cv_pass{pass_no}"] = pred
        row[f"err_vel_cv_pass{pass_no}"]  = (
            abs(pred - meas) / abs(meas) * 100
            if np.isfinite(pred) and np.isfinite(meas) and abs(meas) > 1e-12 else np.nan
        )

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save_results(df)
    print(f"[{idx}] 결과 저장 완료")


def _group_errors(errs):
    """지표별 오차 dict → 종료판정 그룹별 오차(그룹 내 최대) dict."""
    out = {}
    for g, members in TERMINATION_GROUPS.items():
        vals = [errs[m] for m in members if m in errs and np.isfinite(errs[m])]
        out[g] = max(vals) if vals else np.nan
    return out


def _group_errors_df(recent):
    """DataFrame(회차 x 지표) → {그룹: 회차별 최대오차 배열}"""
    out = {}
    for g, members in TERMINATION_GROUPS.items():
        cols = [f"err_{m}" for m in members if f"err_{m}" in recent.columns]
        out[g] = recent[cols].abs().max(axis=1).values
    return out


def is_done():
    """최근 N_CONSECUTIVE회 연속, 모든 그룹의 예측오차가 기준 이하면 종료."""
    df = _load_results()
    adaptive = df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])
    if len(adaptive) < N_CONSECUTIVE:
        return False

    recent = adaptive.tail(N_CONSECUTIVE)
    ge = _group_errors_df(recent)
    ok = np.ones(len(recent), dtype=bool)
    for g in GROUP_NAMES:
        ok &= (ge[g] <= ERR_THRESHOLD)
    return bool(ok.all())


def _converged_objectives(df):
    """최근 N_CONSECUTIVE회 연속 예측오차가 기준 이하인 '지표' 이름 집합.

    이미 수렴한 지표는 _gpr_suggest()의 σ 합산에서 빼서, 남은 실험 예산이
    아직 안 맞는 지표 쪽으로 자연스럽게 쏠리게 함. 판정은 그룹 단위로 하되
    (레인 7개가 다 같이 수렴해야 그 통과가 수렴한 것으로 봄), 제외는 지표 단위로 함.
    """
    adaptive = df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])
    if len(adaptive) < N_CONSECUTIVE:
        return set()

    recent = adaptive.tail(N_CONSECUTIVE)
    ge = _group_errors_df(recent)
    converged = set()
    for g, members in TERMINATION_GROUPS.items():
        if np.all(ge[g] <= ERR_THRESHOLD):
            converged.update(members)
    return converged


# ================== GPR ==================
def _fit_gpr(Xs, y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        # ARD: 변수별 length_scale을 따로 학습 → 어떤 변수가 영향 큰지도 사후 확인 가능
        * Matern(nu=2.5, length_scale=[0.3] * N_DIM, length_scale_bounds=(0.05, 50.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))  # CFD 노이즈 흡수
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def _fit_models(df):
    """목적함수 + 제약조건별 GPR을 따로 학습 → {이름: (모델, log여부)}

    V4에서는 모델 수가 19개(목적 17 + 제약 2)로 늘어 한 회차 학습이 V3보다 오래 걸린다.
    CFD 한 점이 수 분~수십 분인 것에 비하면 여전히 작은 비용이라 그대로 감수함.
    """
    Xs = _normalize(df[PARAM_NAMES].values)
    models = {}
    for name, use_log in MODELED:
        y = df[name].values.astype(float)
        models[name] = (_fit_gpr(Xs, np.log(y) if use_log else y), use_log)
    return models


def _predict_point(df, params):
    """현재까지 데이터로 특정 점의 각 지표 예측값 반환."""
    models = _fit_models(df)
    xs = _normalize([[params[n] for n in PARAM_NAMES]])
    out = {}
    for name, (gpr, use_log) in models.items():
        v = float(gpr.predict(xs)[0])
        out[name] = float(np.exp(v)) if use_log else v
    return out


def _imse_reduction(gpr, cand, ref):
    """후보점 각각을 추가했을 때 참고점들의 평균 분산이 얼마나 줄어드는가.

    GP에서는 점 하나를 추가했을 때 다른 점의 사후분산이 얼마나 줄어드는지가
    닫힌 식으로 나온다(재학습 불필요):

        Δvar(r ; c) = cov(r, c)^2 / var(c)

    이걸 참고점 r 전체에 대해 평균낸 값이 그 후보 c의 IMSE 점수.
    코너 점은 "자기 영향이 미치는 부피"가 작아서 이 값이 작게 나오고,
    안쪽 점은 사방으로 영향이 퍼져 크게 나온다 — 별도 페널티 없이 코너가 후순위가 됨.
    """
    from scipy.linalg import cho_solve

    k1 = gpr.kernel_.k1          # ConstantKernel * Matern (WhiteKernel 제외 = 노이즈 없는 부분)
    Xt = gpr.X_train_

    Kxc  = k1(Xt, cand)                                   # (n_train, n_cand)
    A    = cho_solve((gpr.L_, True), Kxc)                 # K^-1 Kxc
    chat = k1(ref, cand) - k1(Xt, ref).T @ A              # 사후 공분산 cov(ref, cand)
    vC   = k1.diag(cand) - np.einsum("ij,ij->j", Kxc, A)  # 사후 분산 var(cand)
    return (chat ** 2).mean(axis=0) / np.maximum(vC, 1e-12)


def _gpr_suggest(df):
    """
    다음 실험점 제안 — IMSE 기준.

    2단계로 나눠 계산한다.
      1) Sobol 후보 N_CAND개에 대해 σ 합을 구해 상위 N_IMSE_CAND개로 추림
         (IMSE는 후보 하나당 행렬 연산이라 26만 개 전부에 돌리면 비싸고,
          애초에 σ가 낮은 점은 어차피 정보 가치가 없어 버려도 무방)
      2) 그 후보들에 대해서만 IMSE를 계산해 최댓값을 선택

    V3의 `score *= sparsity`는 넣지 않는다 — σ와 sparsity가 둘 다 "기존 점에서
    멀수록 커지는 값"이라 곱하면 코너 선호가 증폭되기 때문(V3 실측으로 확인됨).
    """
    models = _fit_models(df)

    # 정규화 공간 [0,1]^8 에서 후보 생성
    cand_norm = qmc.Sobol(d=N_DIM, scramble=True, seed=len(df)).random(N_CAND)

    # 기존 실험점 + 실패점과 너무 가까운 후보 제거
    #   (실패점 근처는 형상이 성립 안 될 가능성이 높아 같이 배제)
    done = [df[PARAM_NAMES].values]
    failed = _load_failed()
    if len(failed):
        done.append(failed[PARAM_NAMES].values)
    done_norm = _normalize(np.vstack(done))

    from scipy.spatial.distance import cdist
    dmin = cdist(cand_norm, done_norm).min(axis=1)
    keep = dmin >= MIN_DIST_NORM
    if keep.sum() == 0:
        print("  ⚠ 모든 후보가 기존 실험점과 근접 — 거리 제약 해제")
        keep = np.ones(len(cand_norm), dtype=bool)
    cand_norm = cand_norm[keep]

    # 이미 수렴한 지표는 σ/IMSE 합산에서 제외 — 남은 예산이 안 맞는 지표로 쏠리게 함
    converged = _converged_objectives(df)
    active_objs = [n for n in OBJ_NAMES if n not in converged]
    if not active_objs:
        active_objs = list(OBJ_NAMES)
    if converged:
        conv_groups = [g for g, m in TERMINATION_GROUPS.items()
                       if set(m) <= converged]
        print(f"  (수렴 판단되어 다음 실험점 선정에서 제외: {sorted(conv_groups)})")

    # ── 1단계: σ로 후보 추리기 ──
    sig_sum = np.zeros(len(cand_norm))
    for name in active_objs:
        gpr, _use_log = models[name]
        _, sig = gpr.predict(cand_norm, return_std=True)
        sig_sum += sig / (sig.max() + 1e-12)

    n_keep = min(N_IMSE_CAND, len(cand_norm))
    top = np.argpartition(-sig_sum, n_keep - 1)[:n_keep]
    cand_top = cand_norm[top]

    # ── 2단계: 추린 후보에 대해 IMSE 계산 ──
    ref = qmc.Sobol(d=N_DIM, scramble=True, seed=len(df) + 99991).random(N_IMSE_REF)
    score = np.zeros(len(cand_top))
    for name in active_objs:
        gpr, _use_log = models[name]
        red = _imse_reduction(gpr, cand_top, ref)
        score += red / (red.max() + 1e-12)

    best = cand_top[int(np.argmax(score))]
    real = np.round(best * (HI - LO) + LO, 1)
    return to_dict(real)


def _fmt(params):
    return "  ".join(f"{k}={v:.1f}" for k, v in params.items())


# ================== 진단 ==================
def report_relevance():
    """
    학습된 GPR의 ARD length_scale을 뽑아 변수별 영향도를 출력.
    length_scale이 클수록 = 그 변수를 바꿔도 출력이 잘 안 변함 = 영향 작음.
    """
    df = _load_results()
    if len(df) < N_DIM + 2:
        print(f"데이터 부족 (현재 {len(df)}행) — 최소 {N_DIM+2}행 이후에 실행하세요.")
        return

    models = _fit_models(df)
    print(f"\n=== 변수 영향도 (데이터 {len(df)}점 기준) ===")
    for name, (gpr, _use_log) in models.items():
        ls = None
        for p, v in gpr.kernel_.get_params().items():
            if p.endswith("length_scale") and np.ndim(v) == 1:
                ls = np.asarray(v, dtype=float)
                break
        if ls is None:
            print(f"[{name}] length_scale 추출 실패")
            continue
        print(f"\n[{name}] length_scale (작을수록 영향 큼)")
        for pname, v in sorted(zip(PARAM_NAMES, ls), key=lambda t: t[1]):
            bar = "#" * max(1, int(round(20 * min(1.0, 1.0 / max(v, 1e-9)))))
            print(f"  {pname:>18s}: {v:8.3f}  {bar}")


def report_progress():
    """적응샘플링 회차별 그룹 오차 추이 — 학습이 실제로 진행되는지 확인용."""
    df = _load_results()
    adaptive = df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])
    if not len(adaptive):
        print("적응샘플링 데이터가 아직 없습니다.")
        return
    ge = _group_errors_df(adaptive)
    print(f"\n=== 적응샘플링 오차 추이 ({len(adaptive)}회차) ===")
    print("  " + "".join(f"{g:>15s}" for g in GROUP_NAMES))
    for i in range(len(adaptive)):
        print(f"  {i+1:3d}회 " + "".join(f"{ge[g][i]:14.2f}%" for g in GROUP_NAMES))
    print("\n  [최근 10회 중앙값] " + "  ".join(
        f"{g} {np.median(ge[g][-10:]):.2f}%" for g in GROUP_NAMES))


if __name__ == "__main__":
    report_relevance()
    report_progress()
