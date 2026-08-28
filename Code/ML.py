"""
V5 유로+방열핀 9변수 — GPR 대체모델 + IMSE 적응 샘플링 + 예측오차 기반 자동종료

V4(Code3) 대비 변경점

  ① 학습 대상 레인 14개 → std 2개 (통과당 표준편차 1개)
     핀 개수가 설계변수가 되면서 유로 개수가 설계마다 달라진다. GPR은 출력 차원이
     고정이어야 하므로 개수가 변하는 값을 통째로 목적함수로 쓸 수 없다. 처음엔
     상대위치 몇 점(top/mid/bot 등)만 골라 재는 방식을 검토했지만 위치 선정 자체가
     애매해지는 문제가 있어서(짝수 유로에서 정중앙이 없음, 2점만 쓰면 중앙의
     비단조 패턴을 놓침), 유로 전체를 다 재고 그 표준편차 하나로 압축하는 쪽으로
     바꿨다(근거는 result_parser.py 참고). 부수 효과로 모델 수가 19개 → 7개로
     줄어 회차당 학습 시간도 짧아진다.

  ② 종료기준: 목적함수마다 다른 상대/절대오차 대신, 설계공간 변동폭 기준
     단일 규칙으로 통일 (V4 상수 이식 방식 폐기)

     예전 방식(상대오차 1% + std만 절대오차 0.003 LPM)의 문제:
       - "1%"가 목적함수마다 실제 강도가 천차만별이었다. max_temp는 절대값(약
         120도)은 크고 설계마다 변동폭은 작아서(약 0.45도), 1%=1.2도 기준이
         변동폭의 2.66배 — 설계변수를 무시하고 평균값만 답하는 상수 모델도
         통과해버리는 사실상 무의미한 기준이었다(V4 데이터로 실측 확인).
       - std_pass1/2에 쓴 절대오차 0.003 LPM도, 그 유도 근거(eps=0.01 LPM)가
         "V4에서 실측 검증한 값"이라는 것뿐이라 V5(형상·채널수·메시 다 다름)에
         그대로 이식할 근거가 없었다 — 새 캠페인은 이전 캠페인을 몰라도 성립하는
         논리여야 한다.

     새 방식: 모든 목적함수를 절대오차로 통일하되, 기준값을 그 목적함수의
     "DOE 90점에서 실측된 설계공간 표준편차(S_j)"에 비례하게 잡는다.

         |예측 − 실측|  ≤  α · S_j        (α = 0.1, 전 목적함수 공통)

     S_j는 DOE 90점(idx < N_DOE)에서만 딱 한 번 계산하고 이후 고정한다
     (_get_S_j 참고). 적응샘플링 단계 데이터로는 절대 재계산하지 않는데,
     이유는 두 가지:
       1) 순환논리 방지 — 종료 여부를 판단하는 잣대(S_j)와, 그 판단의 대상인
          적응샘플링 오차가 서로 다른 데이터 묶음이어야 한다. DOE는 적응샘플링이
          시작되기 전에 이미 확정되므로 이 조건을 만족한다.
       2) 안정성 — 적응샘플링은 불확실한 영역에 몰아서 찍는 방식이라(균등
          샘플링 아님) 회차마다 S_j 추정치가 출렁이면, "몇 번째 점에서 수렴
          판정났다"는 결론이 언제 멈췄냐에 따라 달라지는 재현성 문제가 생긴다.

     α=0.1의 근거: Q² ≈ 1 − α² 관계로 보면 α=0.1은 Q²≈0.99에 해당 — 대체모델
     검증에서 흔히 쓰는 현실적 기준. α=0.01(Q²≈0.9999)은 지나치게 엄격해서
     가상 시나리오 시뮬레이션 결과 사실상 영원히 수렴하지 않았다.

     ⚠ 이 S_j는 DOE 90점만으로 잰 것이라, 적응샘플링이 DOE보다 더 극단적인
     값을 찾아내면 "진짜" 설계공간 변동폭보다 작게 잡힌 걸 수 있다(→ 기준이
     의도보다 엄격해지는 안전한 방향의 오차). 캠페인 종료 후 전체 데이터
     (DOE+적응샘플링)로 S_j를 다시 계산해 사후 검증용으로 같이 보고할 것 —
     운영 중 쓰는 기준(DOE 고정값)은 안 건드리고, 두 값이 얼마나 다른지만
     논문에 기록한다.

  ③ fin_height는 자유변수가 아니라 8.0mm 고정 (OLHD.FIXED_PARAMS 참고)
     유로 깊이와 같아 우회공간이 없다 — 그 얇고 가변적인 틈을 DOE 전체에서
     메싱해야 하는 리스크와, 우회유동이 열전달을 나쁘게 하는 트레이드오프를
     캠페인에서 피하기 위함. 실제 제작 시엔 조립공차 반영값(7.5mm)으로 최종
     후보 1개만 재검증한다 — 캠페인 자체에는 반영하지 않는다.

  ④ 적응샘플링 후보가 갭 제약을 항상 만족하도록 함
     후보를 박스에서 뽑아 버리는(rejection) 대신 OLHD.decode()로 유효영역 안에
     접어 넣어 생성한다. 무효 후보가 아예 안 생기므로 후보 낭비가 없다.

V4에서 그대로 가져온 것 (근거는 V4 주석에 상세)
  - 적응샘플링은 σ x sparsity가 아니라 IMSE (V3에서 코너 쏠림이 실측으로 확인됨)
  - 회차당 GPR 재학습 최적화: 예측 중복 제거 + joblib 병렬 + n_restarts 3 +
    하이퍼파라미터 5회 재사용 (실측 322.9초 → 4초 안팎)
  - 제약조건(power_module_flow, weight)도 GPR 학습 — GA 단계 필터용
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import qmc
from joblib import Parallel, delayed

from OLHD import (generate_olhd, PARAM_NAMES, LO, HI, N_DIM, DEFAULT_N_DOE,
                  to_dict, decode, normalize, FIXED_PARAMS, I_FIN_THICK, I_FIN_COUNT)
from fins import fin_gap, is_feasible
from paths import RESULTS_PATH, FAILED_PATH
from result_parser import STD_NAMES, TOTAL_FLOW_LPM

# ── 실험 설정 ────────────────────────────────────────────────
N_DOE         = DEFAULT_N_DOE   # 초기 DOE 샘플 수 = 10 x 변수수 (9변수 → 90)
# 무인 장기구동(예: 휴가 중) 안전마진 — S_j 기반 기준이 실전에서 예상보다 쉽게
# 통과되는 목적함수가 있을 경우를 대비해 넉넉하게 잡음. 사람이 결과를 검토한
# 뒤 정상값(예: 3)으로 되돌릴 것.
N_CONSECUTIVE = 20               # 연속 만족 횟수 (모든 그룹이 동시 만족해야 종료)

# ⚠ 무인 장기구동(휴가) 중 절대 조기종료 안 되게 하려고 0.01로 임시 하향(원래 0.1).
#   S_j 자체(DOE 90점 표준편차)는 이 값과 무관하게 그대로 고정되므로, 복귀 후
#   "진짜" 판정(논문용)은 0.1로 되돌려서 이미 쌓인 데이터에 재적용하면 됨 —
#   재실험 불필요, 상수만 바꾸면 즉시 재계산됨.
ALPHA = 0.01   # 절대오차 기준 = ALPHA x S_j (S_j = DOE 90점 기준 설계공간 표준편차, 하단 참고)

# ── 적응 샘플링 설정 ──────────────────────────────────────────
N_CAND        = 65536   # σ로 1차 선별할 후보점 수 (Sobol 균형성 위해 2^16)
N_IMSE_CAND   = 2000    # 그중 σ 상위 몇 개에 대해 IMSE를 계산할지
N_IMSE_REF    = 1024    # IMSE 적분에 쓸 참고점 수 (설계공간 전체에 흩뿌림)
MIN_DIST_NORM = 0.05    # 정규화 공간에서 기존 실험점과 이 거리 미만이면 후보 제외

# ── 목적함수 (5개 = std 2 + 차압 + 온도std + 최고온도) ──────
#    (이름, log변환 여부)
#    std에 log를 쓰지 않는 이유: 값의 범위가 좁고 0 근처에서도 GPR이 선형 공간에서
#    충분히 잘 학습됨 (log는 0 근처에서 오히려 민감도가 과도해짐)
OBJECTIVES = (
    [("pressure_drop", True)]                    # 차압은 스케일이 넓어 log
    + [("temp_std", False), ("max_temp", False)]
    + [(n, False) for n in STD_NAMES]            # std_pass1, std_pass2
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
#    std_pass1/2는 각각 스칼라 하나라 그룹 내 "최악값" 개념이 필요 없지만(멤버 1개),
#    _group_values의 로직을 그대로 재사용할 수 있게 같은 구조(members 리스트)로 둔다.
#    전 그룹 절대오차(|pred_* − *|) 통일 — 기준값은 ALPHA x S_j (아래 _thresholds 참고)
TERMINATION_GROUPS = {
    "pressure_drop": {"members": ["pressure_drop"]},
    "temp_std":      {"members": ["temp_std"]},
    "max_temp":      {"members": ["max_temp"]},
    "std_pass1":     {"members": ["std_pass1"]},
    "std_pass2":     {"members": ["std_pass2"]},
}
GROUP_NAMES = list(TERMINATION_GROUPS)
GROUP_UNIT = {
    "pressure_drop": " Pa",
    "temp_std":      " °C",
    "max_temp":      " °C",
    "std_pass1":     " LPM",
    "std_pass2":     " LPM",
}

_S_J_CACHE = {}   # {목적함수명: DOE 90점 기준 표준편차} — 최초 1회 계산 후 고정, 절대 재계산 안 함


def _get_S_j(df):
    """DOE 90점(idx < N_DOE)에서 목적함수별 표준편차 계산 — 최초 1회만, 이후 고정.

    적응샘플링 데이터가 아무리 쌓여도 이 값은 안 바뀐다 (독립성·재현성 확보 이유는
    상단 모듈 docstring ② 참고). DOE가 아직 안 끝났으면 None을 반환한다.
    """
    global _S_J_CACHE
    if _S_J_CACHE:
        return _S_J_CACHE
    doe_rows = df[df["idx"] < N_DOE]
    if len(doe_rows) < N_DOE:
        return None
    _S_J_CACHE = {name: float(doe_rows[name].std(ddof=0)) for name in OBJ_NAMES}
    print(f"\n[S_j 고정] DOE {N_DOE}점 기준 설계공간 표준편차 — 이후 종료기준에 고정 사용:")
    for name, s in _S_J_CACHE.items():
        print(f"    {name:16s} S_j={s:.5f}  threshold(={ALPHA}xS_j)={ALPHA*s:.5f}")
    return _S_J_CACHE


def _thresholds():
    """그룹별 절대오차 기준(ALPHA x S_j). DOE 미완료면 None."""
    s_j = _get_S_j(_load_results())
    if s_j is None:
        return None
    return {g: ALPHA * s_j[spec["members"][0]] for g, spec in TERMINATION_GROUPS.items()}

_DOE_SAMPLES = None   # 실제로 DOE 단계를 밟을 때만 계산 (lazy)


def _get_doe_samples():
    """generate_olhd()는 후보 LHD를 대량으로 뒤지는 계산이라(수 초 소요) lazy로 둠."""
    global _DOE_SAMPLES
    if _DOE_SAMPLES is None:
        _DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)
    return _DOE_SAMPLES


# 지표별로 [예측값, 실측값, 오차]를 나란히 묶어서 CSV 훑어보기 편하게 정렬
_METRIC_COLS = [c for n in MODELED_NAMES for c in (f"pred_{n}", n, f"err_{n}")]
# fin_gap은 설계변수가 아니라 fin_thick/fin_count에서 나오는 종속값 — 기록만 해둠
_COLUMNS = ["idx"] + PARAM_NAMES + ["fin_gap"] + _METRIC_COLS


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
    row = {n: params[n] for n in PARAM_NAMES}   # 고정 파라미터는 기록 안 함(항상 같음)
    row["reason"] = str(reason)[:300]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(os.path.dirname(FAILED_PATH), exist_ok=True)
    df.to_csv(FAILED_PATH, index=False)
    print(f"  ⚠ 실패 기록 ({len(df)}건 누적): {reason}")


def current_idx():
    """다음에 기록될 실험 번호 (= 지금까지 성공한 실험 수)."""
    return len(_load_results())


# ================== 외부 인터페이스 ==================
def get_next_params():
    """다음 실험할 파라미터 dict 반환 — 자유변수 10개 + 고정 파라미터."""
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
      params  : {변수명: 값} — 자유변수 10개 (+ 고정 파라미터가 섞여 있어도 무방)
      results : {값 이름: 실측값} — MODELED_NAMES가 전부 있어야 함
    """
    df  = _load_results()
    idx = len(df)

    missing = [n for n in MODELED_NAMES if n not in results]
    if missing:
        raise KeyError(f"update_ml에 넘긴 results에 다음 값이 없음: {missing}")

    preds = {n: np.nan for n in MODELED_NAMES}
    errs  = {n: np.nan for n in MODELED_NAMES}
    if idx >= N_DOE:
        global _PENDING_PREDICTION
        cached = _PENDING_PREDICTION
        if cached is not None and cached["idx"] == idx and cached["params"] == params:
            # get_next_params()가 이 점을 고르면서 이미 계산해둔 예측값 재사용
            #   (같은 데이터로 모델 전체를 또 학습하던 중복 제거 — 근사 없이 결과 동일)
            preds = cached["preds"]
        else:
            # 캐시가 없거나 안 맞음(재시작으로 메모리가 날아갔거나, get_next_params
            # 없이 호출된 경우 등) — 안전하게 처음부터 다시 계산. 정상 흐름에선 거의 안 탐.
            print(f"  (참고: 예측 캐시 불일치 — 새로 계산)")
            preds = _predict_point(df, params)
        _PENDING_PREDICTION = None

        # err_*는 참고용 상대오차(%) — CONSTRAINT_NAMES 등 종료판정에 안 쓰는 값도
        # CSV에서 훑어보기 편하도록 그대로 남겨둔다. 실제 종료판정(_group_values)은
        # 이 열을 안 쓰고 pred_*/실측값으로 절대오차를 직접 계산한다.
        for name in MODELED_NAMES:
            errs[name] = abs(preds[name] - results[name]) / abs(results[name]) * 100

    row = {"idx": idx}
    row.update({n: params[n] for n in PARAM_NAMES})
    row["fin_gap"] = fin_gap(params["fin_thick"], params["fin_count"])
    row.update({n: results[n] for n in MODELED_NAMES})
    row.update({f"pred_{n}": preds[n] for n in MODELED_NAMES})
    row.update({f"err_{n}": errs[n] for n in MODELED_NAMES})

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save_results(df)

    if idx >= N_DOE:
        g = _group_values(df.tail(1))
        thr = _thresholds()
        msg = [f"{k} {g[k][0]:.4f}{GROUP_UNIT[k]}" for k in GROUP_NAMES]
        print(f"[{idx}] 예측오차(절대): " + "  ".join(msg))
        if thr is None:
            print(f"      (종료기준 계산 대기 중 — DOE {N_DOE}점 완료 시 S_j 확정)")
        else:
            thr_msg = [f"{k}<={thr[k]:.4f}{GROUP_UNIT[k]}" for k in GROUP_NAMES]
            print(f"      (종료기준: " + "  ".join(thr_msg) + f", {N_CONSECUTIVE}회 연속)")
    print(f"[{idx}] 결과 저장 완료")


def _group_values(rows):
    """DataFrame(회차 x 지표) → {그룹: 회차별 절대오차 |예측 − 실측|}

    전 그룹 공통으로 절대오차를 쓴다(목적함수 고유 단위 그대로, GROUP_UNIT 참고).
    """
    out = {}
    for g, spec in TERMINATION_GROUPS.items():
        per_member = []
        for m in spec["members"]:
            if f"pred_{m}" in rows.columns and m in rows.columns:
                per_member.append((rows[f"pred_{m}"] - rows[m]).abs().values)
        vals = np.max(per_member, axis=0) if per_member else np.full(len(rows), np.nan)
        out[g] = np.asarray(vals, dtype=float)
    return out


def _group_ok(rows):
    """DataFrame → {그룹: 회차별 통과여부 bool 배열}.

    S_j(=DOE 90점 기준 기준값)가 아직 확정 안 됐으면 전부 미통과 처리 — DOE
    끝나기 전엔 종료판정 자체가 성립하지 않아야 하므로(is_done이 이미 DOE
    구간을 걸러내긴 하지만, 이중 안전장치로 여기도 방어).
    """
    thr = _thresholds()
    gv = _group_values(rows)
    if thr is None:
        return {g: np.zeros(len(rows), dtype=bool) for g in GROUP_NAMES}
    return {g: (gv[g] <= thr[g]) for g in GROUP_NAMES}


def _adaptive_rows(df):
    """적응샘플링 구간(예측값이 기록된 회차)만 추림."""
    return df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])


def is_done():
    """최근 N_CONSECUTIVE회 연속, 모든 그룹이 각자의 기준을 만족하면 종료."""
    adaptive = _adaptive_rows(_load_results())
    if len(adaptive) < N_CONSECUTIVE:
        return False

    ok = _group_ok(adaptive.tail(N_CONSECUTIVE))
    return bool(np.all([ok[g].all() for g in GROUP_NAMES]))


def _converged_objectives(df):
    """최근 N_CONSECUTIVE회 연속 기준을 만족한 '지표' 이름 집합.

    이미 수렴한 지표는 _gpr_suggest()의 σ/IMSE 합산에서 빼서, 남은 실험 예산이
    아직 안 맞는 지표 쪽으로 자연스럽게 쏠리게 함. 그룹당 멤버가 1개뿐이라 지표
    단위 제외와 그룹 단위 판정이 사실상 같지만, TERMINATION_GROUPS 구조를
    그대로 재사용하기 위해 이렇게 둔다.
    """
    adaptive = _adaptive_rows(df)
    if len(adaptive) < N_CONSECUTIVE:
        return set()

    ok = _group_ok(adaptive.tail(N_CONSECUTIVE))
    converged = set()
    for g, spec in TERMINATION_GROUPS.items():
        if ok[g].all():
            converged.update(spec["members"])
    return converged


# ================== GPR ==================
_KERNEL_CACHE = {}                 # {지표명: 마지막으로 최적화한 커널} — 적응샘플링 핫패스 전용
_ROUNDS_SINCE_REFRESH = 10 ** 9    # 아주 크게 시작 -> 최초 1회는 무조건 제대로 최적화
_REFRESH_EVERY = 5                 # 몇 회차마다 하이퍼파라미터를 처음부터 다시 찾을지
                                   #   V4 실측: 레인 length_scale이 10회 사이에도 꽤 바뀜
                                   #   (예: 15.4→2.9) — 아직 안정 전이라 10보다 짧은 5로 잡음


def _fit_gpr(Xs, y, n_restarts=3, warm_kernel=None):
    """GPR 하나를 학습.

    n_restarts_optimizer 10 → 3 : V4 실측(같은 데이터, 시드 5개로 로그가능도 비교)
      결과 편차 0.000 — 이 데이터량에서는 3번도 10번과 완전히 같은 최적값을 찾음.

    warm_kernel : 이전에 최적화해둔 커널을 그대로 재사용(하이퍼파라미터 재탐색 생략).
      새 데이터를 반영하는 계산(행렬 분해)은 이 경우에도 매번 정상적으로 하고,
      재사용하는 건 "얼마나 민감한지"라는 설정값뿐임.
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

    if warm_kernel is not None:
        gpr = GaussianProcessRegressor(kernel=warm_kernel, optimizer=None, normalize_y=True)
        gpr.fit(Xs, y)
        return gpr

    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        # ARD: 변수별 length_scale을 따로 학습 → 어떤 변수가 영향 큰지도 사후 확인 가능
        * Matern(nu=2.5, length_scale=[0.3] * N_DIM, length_scale_bounds=(0.05, 50.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))  # CFD 노이즈 흡수
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=n_restarts, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def _fit_models(df, use_cache=False):
    """목적함수 + 제약조건별 GPR을 따로 학습 → {이름: (모델, log여부)}

    use_cache=True (적응샘플링에서 다음 점 고를 때만 씀):
      - 모델들을 코어 수만큼 병렬로 학습(joblib) — 계산 내용은 그대로,
        줄 세우지 않을 뿐이라 결과는 순차 실행과 100% 동일함.
      - _REFRESH_EVERY 회차마다만 하이퍼파라미터를 처음부터 재탐색하고,
        그 사이엔 직전에 찾은 값을 그대로 재사용(_fit_gpr의 warm_kernel).

    use_cache=False (기본값 — 진단용, update_ml의 캐시 불일치 폴백 등):
      캐시를 안 쓰고 항상 처음부터 최적화.
    """
    global _ROUNDS_SINCE_REFRESH
    Xs = normalize(df[PARAM_NAMES].values)

    refresh = (not use_cache) or (not _KERNEL_CACHE) or (_ROUNDS_SINCE_REFRESH >= _REFRESH_EVERY)
    if use_cache:
        _ROUNDS_SINCE_REFRESH = 0 if refresh else _ROUNDS_SINCE_REFRESH + 1

    def _one(name, use_log):
        y = df[name].values.astype(float)
        y = np.log(y) if use_log else y
        warm = None if refresh else _KERNEL_CACHE.get(name)
        return name, _fit_gpr(Xs, y, warm_kernel=warm), use_log

    fitted = Parallel(n_jobs=-1)(delayed(_one)(name, use_log) for name, use_log in MODELED)

    models = {}
    for name, gpr, use_log in fitted:
        models[name] = (gpr, use_log)
        if use_cache and refresh:
            _KERNEL_CACHE[name] = gpr.kernel_
    return models


def _predict_point(df, params):
    """현재까지 데이터로 특정 점의 각 지표 예측값 반환."""
    models = _fit_models(df)
    xs = normalize([[params[n] for n in PARAM_NAMES]])
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


_PENDING_PREDICTION = None   # get_next_params()가 고른 점의 예측값 — update_ml()이 재사용


def _make_candidates(n_done):
    """갭 제약을 만족하는 후보점 생성 → (실제 설계값, 박스 정규화 좌표)

    박스에서 뽑아 무효한 걸 버리는 방식이 아니라, OLHD.decode()로 유효영역 안에
    접어 넣어 만든다. fin_count 반올림 때문에 중복점이 생기므로 한 번 걸러낸다.
    """
    u = qmc.Sobol(d=N_DIM, scramble=True, seed=n_done).random(N_CAND)
    real = decode(u)
    real = np.unique(real, axis=0)   # fin_count 반올림으로 생긴 중복 제거
    return real, normalize(real)


def _gpr_suggest(df):
    """
    다음 실험점 제안 — IMSE 기준.

    2단계로 나눠 계산한다.
      1) 후보 전체에 대해 σ 합을 구해 상위 N_IMSE_CAND개로 추림
         (IMSE는 후보 하나당 행렬 연산이라 전부에 돌리면 비싸고, 애초에 σ가 낮은
          점은 어차피 정보 가치가 없어 버려도 무방)
      2) 그 후보들에 대해서만 IMSE를 계산해 최댓값을 선택

    V3의 `score *= sparsity`는 넣지 않는다 — σ와 sparsity가 둘 다 "기존 점에서
    멀수록 커지는 값"이라 곱하면 코너 선호가 증폭되기 때문(V3 실측으로 확인됨).
    """
    models = _fit_models(df, use_cache=True)

    cand_real, cand_norm = _make_candidates(len(df))

    # 기존 실험점 + 실패점과 너무 가까운 후보 제거
    #   (실패점 근처는 형상이 성립 안 될 가능성이 높아 같이 배제)
    done = [df[PARAM_NAMES].values]
    failed = _load_failed()
    if len(failed):
        done.append(failed[PARAM_NAMES].values)
    done_norm = normalize(np.vstack(done))

    from scipy.spatial.distance import cdist
    dmin = cdist(cand_norm, done_norm).min(axis=1)
    keep = dmin >= MIN_DIST_NORM
    if keep.sum() == 0:
        print("  ⚠ 모든 후보가 기존 실험점과 근접 — 거리 제약 해제")
        keep = np.ones(len(cand_norm), dtype=bool)
    cand_real, cand_norm = cand_real[keep], cand_norm[keep]

    # 이미 수렴한 지표는 σ/IMSE 합산에서 제외 — 남은 예산이 안 맞는 지표로 쏠리게 함
    converged = _converged_objectives(df)
    active_objs = [n for n in OBJ_NAMES if n not in converged]
    if not active_objs:
        active_objs = list(OBJ_NAMES)
    if converged:
        conv_groups = [g for g, s in TERMINATION_GROUPS.items()
                       if set(s["members"]) <= converged]
        print(f"  (수렴 판단되어 다음 실험점 선정에서 제외: {sorted(conv_groups)})")

    # ── 1단계: σ로 후보 추리기 ──
    sig_sum = np.zeros(len(cand_norm))
    for name in active_objs:
        gpr, _use_log = models[name]
        _, sig = gpr.predict(cand_norm, return_std=True)
        sig_sum += sig / (sig.max() + 1e-12)

    n_keep = min(N_IMSE_CAND, len(cand_norm))
    top = np.argpartition(-sig_sum, n_keep - 1)[:n_keep]
    cand_top_real, cand_top_norm = cand_real[top], cand_norm[top]

    # ── 2단계: 추린 후보에 대해 IMSE 계산 ──
    ref = qmc.Sobol(d=N_DIM, scramble=True, seed=len(df) + 99991).random(N_IMSE_REF)
    score = np.zeros(len(cand_top_norm))
    for name in active_objs:
        gpr, _use_log = models[name]
        red = _imse_reduction(gpr, cand_top_norm, ref)
        score += red / (red.max() + 1e-12)

    best_i = int(np.argmax(score))
    real   = cand_top_real[best_i]
    params = to_dict(real)

    if not is_feasible(params["fin_thick"], params["fin_count"]):
        # decode가 보장하므로 정상적으론 안 걸림 — 회귀 방지용 안전망
        raise RuntimeError(f"갭 제약 위반 후보가 선택됨: {params}")

    # 다음 update_ml() 호출에서 재사용할 수 있도록 이 점의 예측값을 미리 계산해둔다.
    #   models는 이미 학습된 상태라 점 하나 예측을 추가하는 건 사실상 공짜 —
    #   여기서 같은 데이터로 모델 전체를 또 학습하던 중복(update_ml 쪽)을 없앤 것.
    xs_best = cand_top_norm[best_i].reshape(1, -1)
    preds = {}
    for name, (gpr, use_log) in models.items():
        v = float(gpr.predict(xs_best)[0])
        preds[name] = float(np.exp(v)) if use_log else v

    global _PENDING_PREDICTION
    _PENDING_PREDICTION = {"idx": len(df), "params": dict(params), "preds": preds}

    return params


def _fmt(params):
    """로그 한 줄 — 자유변수만, fin_count는 정수, 끝에 갭을 덧붙임."""
    parts = []
    for k in PARAM_NAMES:
        v = params[k]
        parts.append(f"{k}={int(v)}" if k == "fin_count" else f"{k}={v:.1f}")
    parts.append(f"(gap={fin_gap(params['fin_thick'], params['fin_count']):.3f})")
    return "  ".join(parts)


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
    adaptive = _adaptive_rows(_load_results())
    if not len(adaptive):
        print("적응샘플링 데이터가 아직 없습니다.")
        return
    gv = _group_values(adaptive)
    ok = _group_ok(adaptive)
    thr = _thresholds()
    print(f"\n=== 적응샘플링 오차 추이 ({len(adaptive)}회차) ===")
    if thr is None:
        print(f"  기준: 아직 미확정 (DOE {N_DOE}점 완료 시 S_j로 확정)")
    else:
        print("  기준(절대오차, ALPHA x S_j): " +
              "  ".join(f"{g}<={thr[g]:.4f}{GROUP_UNIT[g]}" for g in GROUP_NAMES))
    print("      " + "".join(f"{g:>18s}" for g in GROUP_NAMES))
    for i in range(len(adaptive)):
        cells = "".join(f"{gv[g][i]:15.4f}{'o' if ok[g][i] else 'x':>3s}" for g in GROUP_NAMES)
        print(f"  {i+1:3d}회 {cells}")
    print("\n  [최근 10회 중앙값] " + "  ".join(
        f"{g} {np.median(gv[g][-10:]):.4f}{GROUP_UNIT[g]}" for g in GROUP_NAMES))


if __name__ == "__main__":
    report_relevance()
    report_progress()
