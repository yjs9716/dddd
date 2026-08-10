"""
V2 유로 7변수 — GPR 대체모델 + 불확실성 우선 적응 샘플링 + 예측오차 기반 자동종료

V1(2변수) 대비 핵심 변경점
  1) 설계공간 격자 전수탐색 → 랜덤(Sobol) 후보 샘플링
     V1은 0.1단위 격자 75,551점을 전부 나열해 σ를 평가했지만,
     7차원에서 같은 해상도면 후보 수가 천문학적이라 열거 자체가 불가능.
     → 매 회차 N_CAND개 후보를 Sobol로 뽑아 그 중 σ 최대점을 고름.
  2) 중복 제외 방식 변경
     V1은 격자점 정수 매칭으로 기존 실험점을 제외했으나, 연속 후보에서는
     정확히 일치하는 일이 없음 → 기존 점과의 최소거리(MIN_DIST_NORM) 미만이면 제외.
  3) 목적함수는 아직 확정 전 (아래 OBJECTIVES 참고)
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import qmc

from OLHD import generate_olhd, PARAM_NAMES, LO, HI, N_DIM, to_dict
from paths import RESULTS_PATH, FAILED_PATH
# RESULTS_PATH: 실험 결과 + 예측값 (V1 results.csv와 분리된 새 캠페인)
# FAILED_PATH : 리빌드 실패 등으로 해석까지 못 간 실험점 기록
#   (7변수에서는 기하학적으로 성립 불가한 조합이 나올 수 있음
#    → 같은 점을 무한 재시도하지 않기 위해 필요)

# ── 실험 설정 ────────────────────────────────────────────────
N_DOE         = 70     # 초기 DOE 샘플 수 (10 x 변수수 경험칙: 10 x 7 = 70)
ERR_THRESHOLD = 0.5    # 종료 기준: 예측오차 [%]
N_CONSECUTIVE = 3      # 연속 만족 횟수 (모든 목적함수가 동시 만족해야 종료)

# ── 적응 샘플링 설정 (7차원 대응) ──────────────────────────────
N_CAND         = 32768   # 매 회차 σ를 평가할 후보점 수 (Sobol 균형성 위해 2^15)
MIN_DIST_NORM  = 0.05    # 정규화 공간에서 기존 실험점과 이 거리 미만이면 후보 제외

# ── 목적함수 (확정 — 4개) ──────────────────────────────────────
#    이름과 log 변환 여부만 여기서 바꾸면 나머지 코드는 그대로 동작함.
#    4개 다 GPR이 학습 + 불확실성 계산 + 종료판정에 사용 (아래 record-only와 다름):
#      - pressure_drop      : 차압
#      - vel_cv              : 핀뱅크 입구 30레인 속도CV (유량분배 균일도)
#      - temp_std            : 19채널 온도표준편차 — V2는 하단+상단 2회 통과라
#                              V1(1회 통과, 무반응)과 달리 반응할 수 있어 재검증 필요
#      - power_module_temp   : 전원공급모듈(60W, 신규) 온도 — 분기점에서 유량을
#                              충분히 못 받으면 과열될 수 있어 목적함수로 승격
#                              (상대비교 스크리닝 목적 — 블럭모델이라 절대값은 안 믿음)
OBJECTIVES = [
    ("pressure_drop",      True),    # 차압은 스케일이 넓어 log
    ("vel_cv",             False),
    ("temp_std",           False),
    ("power_module_temp",  False),
]
OBJ_NAMES = [o[0] for o in OBJECTIVES]

# 기록만 하고 학습/샘플링/종료판정엔 안 쓰는 컬럼
#   max_temp: 19채널 전체 최고온도 — 블럭모델 절대값을 믿을 수 없어 정밀 최적화
#   대상은 아니지만, 혹시 튀는 조합이 있는지 사람이 훑어보는 안전장치로 계속 기록
RECORD_ONLY = ["max_temp"]

_DOE_SAMPLES = generate_olhd(n_samples=N_DOE, seed=42)

_COLUMNS = (["idx"] + PARAM_NAMES + OBJ_NAMES + RECORD_ONLY
            + [f"pred_{n}" for n in OBJ_NAMES])


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
    df.to_csv(RESULTS_PATH, index=False)


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
    """다음 실험할 파라미터 dict 반환 — {변수명: 값} 7개."""
    df       = _load_results()
    n_failed = len(_load_failed())
    # DOE 단계에서는 '시도한 횟수' 기준으로 진행해야 실패점에서 무한루프에 빠지지 않음
    doe_cursor = len(df) + n_failed

    if doe_cursor < N_DOE:
        params = to_dict(_DOE_SAMPLES[doe_cursor])
        print(f"[DOE {doe_cursor+1}/{N_DOE}] " + _fmt(params))
    else:
        params = _gpr_suggest(df)
        print(f"[불확실성탐색 {doe_cursor-N_DOE+1}회차] " + _fmt(params))

    return params


def update_ml(params, results):
    """
    해석 결과 저장. 적응 단계면 '이번 실험 데이터가 들어가기 전 모델의 예측값'도 함께 기록.
      params  : {변수명: 값} 7개
      results : {값 이름: 실측값} — OBJ_NAMES 4개 + RECORD_ONLY 전부 포함해서 넘길 것
                (result_parser.extract_and_save가 이미 이 형태로 반환함)
    """
    df  = _load_results()
    idx = len(df)

    missing = [n for n in OBJ_NAMES + RECORD_ONLY if n not in results]
    if missing:
        raise KeyError(f"update_ml에 넘긴 results에 다음 값이 없음: {missing}")

    preds = {n: np.nan for n in OBJ_NAMES}
    if idx >= N_DOE:
        preds = _predict_point(df, params)
        msg = []
        for name in OBJ_NAMES:
            actual = results[name]
            err = abs(preds[name] - actual) / abs(actual) * 100
            msg.append(f"{name} {err:.2f}%")
        print(f"[{idx}] 예측오차: " + "  ".join(msg)
              + f"  (종료기준: 전부 {ERR_THRESHOLD}% 이하 {N_CONSECUTIVE}회 연속)")

    row = {"idx": idx}
    row.update(params)
    row.update({n: results[n] for n in OBJ_NAMES})
    row.update({n: results[n] for n in RECORD_ONLY})
    row.update({f"pred_{n}": preds[n] for n in OBJ_NAMES})

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save_results(df)
    print(f"[{idx}] 결과 저장 완료")


def is_done():
    """최근 N_CONSECUTIVE회 연속, 모든 목적함수의 예측오차가 기준 이하면 종료."""
    df = _load_results()
    adaptive = df.dropna(subset=[f"pred_{OBJ_NAMES[0]}"])
    if len(adaptive) < N_CONSECUTIVE:
        return False

    recent = adaptive.tail(N_CONSECUTIVE)
    ok = np.ones(len(recent), dtype=bool)
    for name in OBJ_NAMES:
        err = (recent[f"pred_{name}"] - recent[name]).abs() / recent[name].abs() * 100
        ok &= (err <= ERR_THRESHOLD).values
    return bool(ok.all())


# ================== GPR ==================
def _fit_gpr(Xs, y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        # ARD: 변수별 length_scale을 따로 학습 → 어떤 변수가 영향 큰지도 사후 확인 가능
        #   상한을 V1(5.0)보다 크게 둠: 7변수 중 영향 없는 변수는 length_scale이 매우 커지는
        #   형태로 드러나는데, 상한에 걸리면 "무관한 변수"를 식별할 수 없기 때문
        * Matern(nu=2.5, length_scale=[0.3] * N_DIM, length_scale_bounds=(0.05, 50.0))
        + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-8, 1.0))  # CFD 노이즈 흡수
    )
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(Xs, y)
    return gpr


def _fit_models(df):
    """목적함수별 GPR을 따로 학습 → {이름: (모델, log여부)}"""
    Xs = _normalize(df[PARAM_NAMES].values)
    models = {}
    for name, use_log in OBJECTIVES:
        y = df[name].values.astype(float)
        models[name] = (_fit_gpr(Xs, np.log(y) if use_log else y), use_log)
    return models


def _predict_point(df, params):
    """현재까지 데이터로 특정 점의 각 목적함수 예측값 반환."""
    models = _fit_models(df)
    xs = _normalize([[params[n] for n in PARAM_NAMES]])
    out = {}
    for name, (gpr, use_log) in models.items():
        v = float(gpr.predict(xs)[0])
        out[name] = float(np.exp(v)) if use_log else v
    return out


def _gpr_suggest(df):
    """
    불확실성 우선 탐색 (7차원).
    Sobol로 N_CAND개 후보를 뽑아, 목적함수별 정규화 σ의 합이 최대인 점을 제안.
    기존 실험점 근처(MIN_DIST_NORM 이내)는 후보에서 제외.
    """
    models = _fit_models(df)

    # 정규화 공간 [0,1]^7 에서 후보 생성
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
        # 설계공간이 이미 촘촘히 채워진 경우 — 거리 제약을 풀고 가장 먼 점 사용
        print("  ⚠ 모든 후보가 기존 실험점과 근접 — 거리 제약 해제")
        keep = np.ones(len(cand_norm), dtype=bool)
    cand_norm = cand_norm[keep]

    # 목적함수별 σ 정규화 후 합산 → 여러 지도가 고르게 정확해지도록
    score = np.zeros(len(cand_norm))
    for name, (gpr, _use_log) in models.items():
        _, sig = gpr.predict(cand_norm, return_std=True)
        score += sig / (sig.max() + 1e-12)

    best = cand_norm[int(np.argmax(score))]
    real = np.round(best * (HI - LO) + LO, 1)
    return to_dict(real)


def _fmt(params):
    return "  ".join(f"{k}={v:.1f}" for k, v in params.items())


# ================== 진단: 어떤 변수가 실제로 영향을 주는가 ==================
def report_relevance():
    """
    학습된 GPR의 ARD length_scale을 뽑아 변수별 영향도를 출력.
    length_scale이 클수록 = 그 변수를 바꿔도 출력이 잘 안 변함 = 영향 작음.
    7변수 중 실제로 의미 있는 변수가 몇 개인지 판단해서, 다음 캠페인에서
    변수를 줄일지 결정하는 근거로 사용.
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


if __name__ == "__main__":
    report_relevance()
