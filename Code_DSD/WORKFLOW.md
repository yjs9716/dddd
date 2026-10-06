# V6 — DSD 선별 → OLHD + GPR 적응샘플링

V5(`Code/`, 9변수, 핀 공유)를 대체하는 새 캠페인이다. V5 코드와 데이터는 건드리지 않는다.

## 논리

1. **후보 11변수**: V5 9변수에서 핀 두께·개수를 1차/2차 통과별로 분리한다. 1차 통과 뒤 전원모듈로 분기되면서 통과별 채널당 유량이 달라지기 때문이다.
2. **1단계 DSD (29회)**: 결정적 선별 설계를 쓴다. 변수 11개에 가짜 인자 3열을 더해 14열 컨퍼런스 행렬을 만들고, 이를 거울상으로 접은 뒤 중심점 1회를 더한다.
3. **선별 판정**: 판정 규칙은 실험 전에 고정한다(`DSD_analysis.py` 상단). 효과 성분은 두 조건을 모두 만족할 때만 인정한다.
   - 가짜 인자 바닥과 통계적으로 구분된다(p ≤ 0.10).
   - 응답 분산의 2% 이상을 설명한다.

   모든 응답에서 인정되는 성분이 없으면 그 변수를 고정한다. 고정값은 중량이 최소인 수준으로 정한다.
4. **2단계**: 활성 변수만으로 OLHD(10 × 활성 변수 수)를 돌리고, 이어서 IMSE 적응샘플링을 한다. 종료기준은 V5와 같다(|예측 − 실측| ≤ 0.1·S_j, 3회 연속).

## 실행 순서

| 단계 | 명령 | 산출물 (`Result/DSD`, `Result/OLHD`) |
|---|---|---|
| 격자 민감도 (DSD 전) | `python grid_convergence.py` | `Result/GCI/gci_edge_results.csv`, `gci_edge_summary.json` → `icepak.py`의 `MIN_ELEMENTS_ON_EDGE` 확정 (2~6 비교, 최대 셀 1.0 mm) |
| 실험표 확인 | `python DSD.py` | `dsd_plan.csv` (첫 실행 시 자동 생성) |
| 1단계 해석 | `python main.py` | `results_dsd.csv`, `result_dsd_000.csv`… |
| 선별 판정 | `python DSD_analysis.py` | `dsd_effects.csv`, `screening_decision.json` |
| 2단계 해석 | `python main.py` | `results_v6.csv`, `result_000.csv`… |
| 진행 확인 | `python ML.py` | 캠페인 상태, 적응샘플링 오차 추이 |

`main.py`는 캠페인 상태를 보고 이어서 진행한다. DSD가 끝나면 멈추고 선별 판정을 요구한다.
DSD run이 실패하면 `failed_dsd.csv`에 기록된다. 원인을 고친 뒤 `python -c "import ML; ML.retry_failed_dsd()"`로 재시도한다.

## 파일

| 파일 | 역할 | V5 대비 |
|---|---|---|
| `params.py` | 후보 11변수 범위, `decode`(뱅크별 핀 개수 접어 넣기), 선별 결과 반영(`Screening`) | 신규 |
| `responses.py` | 목적함수·제약 목록 | ML.py에서 분리 |
| `DSD.py` | 컨퍼런스 행렬(Paley), 29회 실험표 | 신규 |
| `DSD_analysis.py` | 주효과·곡률 추정, 가짜 인자 기반 검정, 선별 판정 | 신규 |
| `OLHD.py` | 활성 변수 OLHD | 변수 목록을 선별 결과에서 받음 |
| `ML.py` | 캠페인 단계 관리, GPR, IMSE, 종료판정 | DSD 단계 추가, 활성 변수 차원 |
| `fins.py` | 핀 배치 수식 (뱅크별) | `max_fin_count` 부동소수점 오차 수정(t = 1.7 mm에서 19 → 20개) |
| `Solidworks.py` | 전역변수 11개 기록, 뱅크별 갭 검증 | 변수 11개 |
| `icepak.py` | 뱅크별 측정면, 단계별 결과 경로 | V5 스크립트에서 핀 관련 부분만 변경 |
| `result_parser.py` | 뱅크별 유로 개수로 행 위치 계산 | n1 ≠ n2 대응 |
| `main.py` | 전체 루프 | 단계 분기 |
| `paths.py` | 작업폴더, SolidWorks 준비사항 | V6 폴더 |

## 실행 전 확인

- 작업폴더는 `E:\Thermal_Anlaysis\Liquid_plate\261006`(`paths.py`의 `BASE_V6`)이다.
- SolidWorks 전역변수 11개와 뱅크별 갭 수식을 만든다(`paths.py` 상단 참고).
- `icepak.py`의 `FIN_BANK1/2_Y_START`가 맞는지, 그리고 측정면이 두 뱅크 유로에 정확히 놓이는지 DSD run 0에서 AEDT 화면으로 확인한다.
- `result_parser.py`의 `FULL_SOLID_VOLUME_MM3`는 판재 외형이 바뀌었으면 다시 잰다.
- `DSD_analysis.py`의 사전 고정 규칙(`ALPHA`, `SHARE_MIN`, `PROTECTED`, `MAX_DROP`, `FALLBACK_LEVEL`)은 **DSD 시작 전에** 확정한다.
- 변수 범위는 V5와 같되 세 가지가 다르다. 전원입구 두께는 3~10 mm(V5는 3~20), 최소 핀 갭은 2.0 mm(V5는 2.5), 핀 개수는 10~24개(V5는 10~21)다. 근거는 `params.py`와 `fins.py` 주석에 있다. 범위를 바꾸려면 `params.py`의 `CANDIDATE_SPEC`과 `fins.py`의 `MIN_GAP_MM`을 고치면 된다.
- 제작 최소 갭(예: 2.5 mm)은 실험 범위가 아니라 최적화 단계의 제약으로 건다.
- 가장 촘촘한 조합(두께 1.5 mm, 핀 24개, 갭 2.02 mm)은 DSD 실험표에 들어 있다. DSD를 시작하기 전에 이 형상을 한 번 해석해서 메싱이 되는지, 갭 방향 셀이 3개 이상인지 확인한다.
