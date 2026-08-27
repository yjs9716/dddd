# 냉각판 V5 — 유로+방열핀 10변수 최적화 (내부망 반입용)

V4(유로 8변수, `Code3`)에 **방열핀 변수화**를 추가한 버전. 설계변수 1개를
성능 트레이드오프가 없다는 근거로 고정값으로 옮기고, 방열핀 두께·높이·개수
3개를 새로 추가해 자유변수 10개가 됐다. 이 폴더(`Code/`) 전체를 내부망으로
복사해서 사용.

---

## 1. 설계변수 (자유 10개 + 고정 1개)

| # | 변수명 (SolidWorks 글로벌 변수명과 동일해야 함) | 범위 | 단위 |
|---|---|---|---|
| 1 | `input_thick` | 15 ~ 35 | mm |
| 2 | `input_angle` | 90 ~ 150 | deg |
| 3 | `power_input_thick` | 3 ~ 20 | mm |
| 4 | `mid_thick` | 15 ~ 35 | mm |
| 5 | `mid_angle` | 90 ~ 140 | deg |
| 6 | `mid_input_thick` | 15 ~ 35 | mm |
| 7 | `output_thick` | 15 ~ 35 | mm |
| 8 | `fin_thick` | 1.5 ~ 3.0 | mm |
| 9 | `fin_height` | 6.0 ~ 7.9 | mm |
| 10 | `fin_count` | 10 ~ 21 | 개 (정수) |

**고정 파라미터** (탐색하지 않지만 SolidWorks에는 값을 넣어줘야 함):

| 변수명 | 값 | 왜 고정인가 |
|---|---|---|
| `power_output_thick` | 25 mm | V4 데이터 211점으로 partial dependence를 뽑아보니 15~40mm 전 구간에서 목적함수들이 같은 방향(대부분 40mm 선호, 반대쪽은 1.9%/0.17%로 무시 가능)이라 트레이드오프가 없었음. 탐색할 이유가 없는 "이미 결정 끝난 변수"라 예산을 방열핀 쪽으로 돌림. 값 자체(25)는 성능이 아니라 형상 미관 기준으로 선택 |

정의 위치: `OLHD.py`의 `PARAM_SPEC`(자유변수) + `FIXED_PARAMS`(고정값) **두 곳뿐**.
범위를 바꾸려면 여기만 수정하면 OLHD / ML / SolidWorks / result_parser가 전부 따라감.

> `output_thick`은 고정하지 않고 그대로 자유변수로 남겼다. 방향은 갈리지 않지만(35mm
> 선호) `pressure_drop` 전체 변동의 14.5%를 담당할 만큼 영향이 크고, 실측에서
> "두꺼울수록 유량이 더 균일해지는"(직관과 반대 방향) 거동이 나와 원인을 확정하지
> 못했다. 확실치 않은 걸 고정하면 그 구간을 영영 못 보게 되므로 남겨둠.

### 유로 순환구조 (V4와 동일)

```
입구 → 하단(+X 방향, 8채널 1차 통과) → 분기 ┬→ 전원공급모듈 분기 ┐
                                             └→ 상단(−X 방향, 같은 8채널 2차 통과) ┴→ 합류 → 출구
```

- 총 유량(4LPM 고정)이 분기점에서 전원모듈 vs 상단패스로 갈림
- 전원모듈 분기 유량은 온도가 아니라 **유량비율**로 추적

### 방열핀 배치 — 등간격, 갭은 종속 계산값 (`fins.py` 신규)

```
[벽] g [핀] g [핀] g ... g [핀] g [벽]
```

핀 N개 → 유로(갭) N+1개. **폐합조건 하나로 상단벽↔핀, 핀↔핀, 핀↔하단벽 간격이
전부 자동으로 같아진다**:

```
L = N·t + (N+1)·g          (L = 핀뱅크 길이 86.5mm, 상수)
g = (L − N·t) / (N+1)
```

- 가변피치(등차수열)도 검토했으나 구현 복잡도 대비 이득이 불확실해 등간격으로 확정
- **갭 최소 제약 `g ≥ 2.5mm`** — 밀링 가공 시 갭이 너무 좁으면 유로가 막히고
  메시도 못 자름. `fin_thick`·`fin_count` 박스에서 이 조건을 만족하는 영역은
  약 70%뿐이라(`t=3.0`이면 `N`은 15까지만 허용), `OLHD.decode()`가 박스에서
  뽑아 버리는 방식(rejection) 대신 **유효영역 안으로 접어 넣어** 생성한다
  (자세한 내용은 4-(4)절)

---

## 2. V4 대비 무엇이 바뀌었나

### (1) 레인 측정: 통과당 7개 → 3개 (top/mid/bot) ★ 가장 중요

`fin_count`가 설계변수가 되면서 유로 개수가 설계마다 11~22개로 달라진다.
"몇 번째 유로"라는 인덱스는 설계마다 다른 물리적 위치를 가리키게 되고,
GPR은 출력 차원이 고정이어야 해서 개수가 변하는 값을 통째로 목적함수로 쓸 수 없다.

→ 유로 개수와 무관하게 항상 같은 의미를 갖는 **상대위치 3점**(최상단/중앙/최하단)만
측정. 측정면의 실제 좌표는 `fins.measure_channels()`가 `fin_thick`/`fin_count`로부터
매 설계마다 계산한다.

- 잃는 것: "중간의 특정 유로 하나만 막힘" 같은 비단조 편차는 못 봄
- 다만 헤더 분배 유동의 지배적 실패모드는 위→아래 단조 편중이나 중앙 vs 양끝
  포물선 형태라 3점이면 주된 패턴은 잡힘. 유로 개수가 가변인 이상 "전체 측정"은
  선택지 자체가 없으므로 손해라기보다 불가피한 근사

### (2) 종료기준: 레인만 상대오차 → 절대오차로 교체 ★

V4에서 211점을 쌓고도 레인 그룹(`lane_pass1`/`lane_pass2`)은 상대오차 1%를
3회 연속 만족한 적이 없었다. 데이터 부족이 아니라 기준 자체가 구조적으로
도달 불가능했기 때문 — 레인 유량은 총유량을 여러 개로 나눈 값이라, 설계가
좋아져 유량이 균일해질수록 분모(그 레인의 예측값)가 작아져서 상대오차가
증폭된다(CV에서 겪었던 문제가 한 단계 아래에서 재현된 것).

→ 레인만 분모를 "그때그때 예측값"이 아니라 "총유량 4 LPM"이라는 고정값으로 교체:

| 그룹 | 기준 |
|---|---|
| `pressure_drop` / `temp_std` / `max_temp` | 상대오차 ≤ 1% (그대로 — 문제 없었음) |
| `lane_pass1` / `lane_pass2` | 절대오차 ≤ 0.01 LPM (= 총유량의 0.25%) |

⚠ V5에서는 이 기준이 V4보다 상대적으로 느슨해진다. V4는 레인이 통과당 7개라
하나당 약 0.57 LPM이었지만, V5는 유로가 11~22개라 하나당 0.18~0.36 LPM이다.
같은 0.01 LPM이 레인 대비 1.8% → 2.8~5.5%가 된다. 그래도 이 기준을 쓰는 이유는
설계 판단에서 의미 있는 게 "시스템 총유량 대비 얼마나 잘못 배분됐나"이고, 그 값은
유로를 몇 개로 쪼갰든 달라지지 않기 때문 — 레인 대비 비율로 잡으면 핀 개수가
많은 설계일수록 기준이 저절로 빡세져서 설계마다 다른 잣대를 들이대는 꼴이 된다.

### (3) `power_output_thick` 자유변수 → 고정값

1절 표 참고. partial dependence로 트레이드오프가 없음을 확인하고 고정, 예산을
방열핀 변수로 이전.

### (4) 갭 제약을 만족하는 후보만 생성 (`OLHD.decode`) ★

`(fin_thick, fin_count)` 박스에서 무작위로 뽑고 버리는(rejection) 방식은 무효
영역이 약 30%라 그만큼 후보를 낭비하고 LHD의 층화도 깨진다. 대신 `fin_count`를
"그 두께에서 허용되는 범위" 안으로 접어 넣는다(중첩 샘플링):

```python
N_max(t) = (L − g_min) / (t + g_min)                     # fins.max_fin_count()
N        = round(N_lo + u · (min(N_hi, N_max(t)) − N_lo))
```

⚠ 반올림 순서 주의 — **두께를 먼저 반올림한 뒤** 허용 개수를 계산해야 한다.
반대로 하면 이런 사고가 난다: 원값 `t=2.1554`(허용 개수 18) → `N=18` 선택 →
그 다음 `t`가 `2.2`로 올림 반올림 → 실제 갭이 `(86.5−18×2.2)/19=2.468mm`로
제약을 깸. 구현 중 실제로 이 순서로 짰다가 통합 테스트(`is_feasible` 안전망)가
잡아냈고, 두께 반올림을 먼저 하도록 고쳐서 20만 개 후보 전수 검증(위반 0건)함.

이 접힘 때문에 `fin_thick`과 `fin_count`는 서로 독립이 아니게 되는데(두께가
두꺼울수록 개수의 유효범위가 좁아짐), 이건 실제 제약이 만든 삼각형 모양
유효영역을 그대로 반영한 것이라 정상이다.

### (5) 학습 모델 수 19개 → 11개

레인이 14개 → 6개로 줄면서 목적함수 17개 → 9개, 제약조건 2개는 그대로라
총 학습 모델이 19개 → 11개. 회차당 GPR 재학습 시간도 그만큼 짧아짐.

### (6) `fin_count` 정수 취급

`fin_count`는 SolidWorks 선형패턴의 인스턴스 개수라 정수여야 한다.
`OLHD.decode()`가 반올림해서 만들고, `to_dict()`가 `int()`로 캐스팅하며,
`Solidworks.update_sw()`가 float가 흘러들어오면 즉시 예외를 낸다.

---

## 3. 파일 구성

| 파일 | V4 대비 | 설명 |
|---|---|---|
| `fins.py` | **신규** | 핀 배치 수식의 단일 출처 — 갭 공식, 최대 개수, 갭 제약 판정, 측정유로 위치 |
| `OLHD.py` | 재작성 | 10변수 LHD + 고정 파라미터 + 갭 제약을 만족하는 `decode()` |
| `ML.py` | 재작성 | GPR + IMSE 적응샘플링 + 그룹별(상대/절대 혼재) 종료판정 + 실패기록 + 영향도진단 |
| `result_parser.py` | 재작성 | 레인 3점×2통과 파싱, 근사 검산(`_check_closure`), 유량·중량 환산 |
| `icepak.py` | 재작성 | 측정 사각형을 상수 좌표 대신 `fins.measure_channels()` 계산 위치에 배치, Fields Summary 항목 반복문 생성 |
| `Solidworks.py` | 재작성 | 글로벌 변수 11개(자유10+고정1) 일괄 set, `fin_count` 정수 검증, 갭 제약 사전검증 |
| `main.py` | 소폭 수정 | 로직은 V4와 동일(재작성 이유 없음). 회차 소요시간 로그 추가 |
| `paths.py` | 신규 경로 | 작업폴더 `260827` |

캠페인 실행에 필요한 모듈은 이 8개뿐이고, `OLHD_PLOT.py`는 DOE 분포를
눈으로 확인하고 싶을 때만 별도로 돌리는 진단용 스크립트.

### 값이 정의된 위치 (단일 출처)

| 값 | 정의 위치 | 쓰는 곳 |
|---|---|---|
| 설계변수 이름·범위(`PARAM_SPEC`), 고정값(`FIXED_PARAMS`) | `OLHD.py` | ML / Solidworks / result_parser |
| DOE 점 수(`DEFAULT_N_DOE` = 10 × 변수수 = 100) | `OLHD.py` | `ML.N_DOE` |
| 핀뱅크 길이·최소갭(`FIN_SPAN_MM`, `MIN_GAP_MM`), 갭·측정위치 공식 | `fins.py` | OLHD / Solidworks / icepak / result_parser |
| 발열채널 개수(`N_SOURCE`) | `icepak.py` | `result_parser`의 CSV 행 인덱스 |
| 측정점 개수·라벨(`N_MEASURE`, `MEASURE_LABELS`) | `fins.py` | `icepak`/`result_parser`의 CSV 행 인덱스 |
| PAO 밀도(`PAO_DENSITY`) | `icepak.py` | `result_parser`의 중량 계산 |
| 종료판정 그룹·기준(`TERMINATION_GROUPS`) | `ML.py` | `finalize_campaign.py`(재판정 시 그대로 import) |

> 변수를 추가/삭제하면 `PARAM_SPEC`만 고치면 DOE 점 수까지 자동으로 따라감.
> 핀뱅크 길이가 바뀌면 `fins.FIN_SPAN_MM` 하나만 고치면 갭 공식·측정위치·
> `max_fin_count`가 전부 따라감.

### `fins.py` — 핵심 함수

```python
fin_gap(fin_thick, fin_count) -> float          # 등간격 갭 [mm]
max_fin_count(fin_thick) -> int                 # 갭≥2.5mm를 만족하는 최대 개수
is_feasible(fin_thick, fin_count) -> bool       # 갭 제약 판정
channel_offsets(fin_thick, fin_count) -> list   # 유로 N+1개의 (오프셋, 폭)
measure_channels(fin_thick, fin_count) -> list  # 측정 3점의 (라벨, 오프셋, 폭)
```

`python fins.py`로 직접 실행하면 두께별 최대 개수 표, 갭 표, 폐합조건 검산,
측정유로 좌표를 바로 확인할 수 있다.

### `icepak.py` 인터페이스 계약 (V4와 동일 시그니처 유지)

```python
def connect_aedt():
    ...
    return desktop, None

def run_icepak(desktop, ipk, step_file, idx, params):
    ...
    return ipk, result_path, pao_volume_mm3
```

**CSV 출력 행 구조** (`skiprows=5` 이후 — Fields Summary에 `Calculation:=`
추가한 순서 = CSV 행 순서, 총 16행):

| 행 | 내용 | 쓰는 열 |
|---|---|---|
| 0~7 | source01~08 온도 | Max(8) → `max_temp`, Mean(9) → `temp_std` |
| 8 | Fan1_Passage 차압 | Mean(9) |
| 9~11 | V_inlet_top/mid/bot (1차 통과) 속도 | Mean(9) × Area(11) |
| 12~14 | V_inlet2_top/mid/bot (2차 통과) 속도 | Mean(9) × Area(11) |
| 15 | Rectangle1 (전원모듈 분기 입구) 법선방향 속도 | Mean(9) × Area(11) |

열 인덱스(`Min=7 / Max=8 / Mean=9 / Stdev=10 / Area=11`), 유량을
`Mean×Area`로 계산하는 이유(메시 경계 셀이 면적에 섞이는 왜곡 상쇄),
2차 통과 부호 처리, 측정면 배치 원칙(유로 단면을 모자라지 않게 덮되 옆
유로로 넘어가지 않게)은 V4에서 그대로 유지 — 상세 근거는 `result_parser.py`,
`icepak.py` 주석 참고.

⚠ V5 신규 확인사항: 갭이 최소 2.5mm까지 좁아지므로 메시가 갭을 2~3셀 이상으로
가르는지, 측정면 z 방향이 핀 높이가 아니라 **유로 깊이 전체**를 덮는지
(핀이 유로보다 낮으면 핀 위로 넘어가는 우회 유량까지 세어야 함) 첫 실행에서
반드시 확인.

### 작업폴더 / 경로

작업폴더: `E:\Thermal_Anlaysis\Liquid_plate\260827`
모든 경로는 `paths.py` 한 곳에서만 정의.

| 상수 | 실제 경로 | 용도 |
|---|---|---|
| `PART_PATH` | `...\Solidworks\plate_base.SLDPRT` | 형상 파트 |
| `ASM_PATH` | `...\Solidworks\flowpath.SLDASM` | 어셈블리 |
| `STEP_DIR` | `...\Solidworks\Step\` | 실험점별 STEP 저장 |
| `AEDT_PROJ_PATH` | `...\AEDT\thermal_test` | Icepak 프로젝트 |
| `ICEPAK_RESULT_DIR` | `...\Result\` | Icepak 원본 CSV |
| `RESULTS_PATH` | `...\Result\results_v5.csv` | 실험 결과 + 예측값 |
| `FAILED_PATH` | `...\Result\failed_v5.csv` | 형상 미성립 등 실패점 |

> ⚠ **`results_v5.csv` 삭제 금지.** 형상↔파라미터 대응은 이 CSV가 유일한 기록.

### SolidWorks Equation Manager 준비사항 (V5 신규)

전역변수 11개(자유 10 + `power_output_thick` 고정값)가 전부 있어야 함. 핀
간격은 변수가 아니라 **수식으로** 걸어둘 것 — 파이썬이 갭을 직접 써넣지
않고 SolidWorks가 스스로 계산하게 두는 이유는, 두 곳에서 각각 계산하면
언젠가 반드시 어긋나기 때문:

```
"fin_gap" = (86.5 - "fin_count" * "fin_thick") / ("fin_count" + 1)
```

핀은 선형패턴으로 만들고, 패턴 간격 = `"fin_gap" + "fin_thick"`, 인스턴스
개수 = `"fin_count"`, 첫 핀의 상단벽 오프셋 = `"fin_gap"`으로 묶으면 상단벽↔핀
/ 핀↔핀 / 핀↔하단벽 간격이 전부 자동으로 같아진다.

---

## 4. 반입 전 확인 필요 ⚠

### (1) 핀뱅크 길이 `FIN_SPAN_MM = 86.5`

V4(Code3) 형상을 역산하면 핀 6개·`t=2.5`·갭 7.357142857(피치 9.857142857)로
총길이 **66.5mm**였다(`fins.py`의 폐합식과 정확히 일치하는 걸로 검증함). V5는
86.5mm를 전제하므로 핀뱅크가 늘어난 신규 형상이어야 한다 — SolidWorks 실물과
반드시 대조.

### (2) 유로 깊이 `CHANNEL_DEPTH_MM = 7.9`

`fin_height` 상한이 7.9mm인데 V4의 유로 깊이는 7.5mm였다. 유로가 핀보다 깊거나
같아야 하므로 실제 깊이 확인 필요.

### (3) 핀뱅크 측정 기준좌표 (`icepak.py`)

`FIN_BANK1_Y_START`(−101.25), `FIN_BANK2_Y_START`(−4.749999983)는 V4 형상에서
역산한 값. 핀뱅크 길이가 바뀌었다면 벽 위치도 달라졌을 수 있어, 측정면이 유로
안에 정확히 들어가는지 **첫 실행에서 AEDT 화면으로 직접 확인**할 것.

### (4) `FULL_SOLID_VOLUME_MM3` (중량 계산 상수)

판재(plate+plate_base) 바깥 치수가 고정이라는 전제의 상수(2341073.1 mm³).
핀뱅크 길이가 늘어나 판재 외형 자체가 바뀌었다면 SolidWorks에서 다시 실측할 것
(핀 자체는 유로 안쪽이라 영향 없음 — 핀이 차지하는 부피는 알루미늄 부피에
이미 반영되어 SolidWorks가 알려줌).

### (5) 메시 크기 — 갭이 2.5mm까지 좁아짐

`icepak.py` 상단 `MESH_REGION_X/Y/Z`, `GLOBAL_MESH_X/Y/Z`. 최소 갭이 V4(7.36mm)보다
훨씬 좁아졌으므로, 좁은 갭 설계에서 메시가 최소 2~3셀 이상으로 갭을 가르는지
확인 필요. 부족하면 로컬 메시를 더 조여야 함.

### (6) 초기 DOE 점 수 = 100

`10 × 변수수` 경험칙(10변수). `OLHD.DEFAULT_N_DOE`가 자동 계산, `ML.N_DOE`가 그대로 씀.
V4(80점)보다 20점 늘어남 — 실행 1회당 SolidWorks 리빌드 + Icepak 풀 해석이므로
시간 예산 재확인 필요.

### (7) 목적함수 — 확정 (9개)

| # | 목적함수 | 방향 | 비고 |
|---|---|---|---|
| 1 | `pressure_drop` (차압) | 최소화 | log 변환 |
| 2 | `temp_std` (8채널 온도표준편차) | 최소화 | |
| 3 | `max_temp` (8채널 최고온도) | 최소화 | |
| 4~6 | `lane1_top/mid/bot` (1차 통과 측정 유량) | 균일화 목표 | GPR 직접 학습 대상 |
| 7~9 | `lane2_top/mid/bot` (2차 통과 측정 유량) | 균일화 목표 | GPR 직접 학습 대상 |

레인을 CV로 압축하지 않고 개별 유량을 그대로 학습하는 이유(CV는 좋은 설계일수록
분모가 작아져 오차를 증폭시킴 — V2 364점·V4 211점을 돌리고도 CV 기준 1%를 한 번도
못 넘은 이유)는 V4에서 확정된 결론이라 V5도 그대로 따름. CV(`vel_cv_pass1/2`)는
예측된 레인 유량으로부터 계산해서 GA 입력·참고 지표로만 계속 씀.

**제약조건용 지표** (GPR 학습·예측은 목적함수와 동일하게 하되 적응샘플링/종료판정에는 관여 안 함):

| 지표 | 용도 |
|---|---|
| `power_module_flow` | 전원모듈 분기 유량비율 (0~1) |
| `weight` | 알루미늄 + PAO 총 중량 [kg] |

### (8) 중량 계산 방식 (V4와 동일)

```
PAO 부피 = FULL_SOLID_VOLUME_MM3 − 알루미늄 부피(SolidWorks, 매 idx 리빌드)
weight  = 알루미늄 질량 + PAO 부피 x 794 kg/m^3
```

`Solidworks.update_sw`가 리빌드 직후 (알루미늄 질량, 부피)를 반환 →
`main.py`가 `result_parser.extract_and_save`로 전달. `icepak.run_icepak`이
반환하는 `pao_volume_mm3`는 중량 계산엔 안 쓰고 교차검증 로그로만 사용.

---

## 5. 결과 파일 구조

### `results_v5.csv` — ML.py가 관리하는 캠페인 본체

```
idx, [설계변수 10개], fin_gap,
pred_pressure_drop, pressure_drop, err_pressure_drop,
pred_temp_std,      temp_std,      err_temp_std,
pred_max_temp,      max_temp,      err_max_temp,
pred_lane1_top, lane1_top, err_lane1_top,   (mid/bot 반복)
pred_lane2_top, lane2_top, err_lane2_top,   (mid/bot 반복)
pred_power_module_flow, power_module_flow, err_power_module_flow,
pred_weight,        weight,        err_weight,
pred_vel_cv_pass1, vel_cv_pass1, err_vel_cv_pass1,
pred_vel_cv_pass2, vel_cv_pass2, err_vel_cv_pass2
```

- `fin_gap`은 설계변수가 아니라 `fin_thick`/`fin_count`에서 나오는 종속값 — 기록만
- `pred_*`/`err_*`는 적응샘플링 단계부터 채워짐 (DOE 구간은 `NaN`)
- `err_*` = 상대오차 [%] — 종료판정에서는 레인 그룹만 이 열을 안 쓰고
  `pred_*`와 실측값으로 절대오차를 직접 계산함(2절 (2) 참고)
- 저장할 때마다 컬럼 순서를 다시 맞추므로 기존 CSV를 이어받아 재개해도 배치 유지

> ⚠ **`results_v5.csv` 삭제 금지.**

### `finalize_campaign.py` — 종료 후 여분 데이터 잘라내기 (선택적)

`ML.is_done()`이 종료를 판정하면 캠페인은 거기서 멈추므로 정상 흐름에서는
필요 없다. 종료 판정 후에도 더 돌려 여분 데이터를 쌓았거나, 기준을 바꿔
재판정하고 싶을 때 씀. 판정 기준은 `ML.py`에서 그대로 import해 쓰므로
임계값을 두 곳에 중복해서 적지 않는다.

```
python finalize_campaign.py   # results_v5_final.csv 생성, 원본은 안 건드림
```

---

## 6. GPR 이후 단계 (참고 — 아직 코드화 안 함)

V4와 동일한 절차를 따름:

1. 이 캠페인으로 목적함수 9개 + 제약조건 2개의 GPR 지도를 전역에 걸쳐 완성
2. 완성된 GPR 지도 위에서 유전알고리즘(NSGA-II 등)으로 파레토 프론트 탐색
   — 제약조건 필터(전원모듈 유량비율, 중량)를 먼저 걸고, 필터는 예측 평균이
   아니라 **평균 + kσ**로 보수적으로
3. 파레토 후보군에서 최종 1개 선택
4. 최종 후보 몇 개는 반드시 실제 SolidWorks+Icepak으로 재검증

---

## 7. 실행

```bash
python main.py              # 캠페인 실행 (종료조건 만족까지 자동 반복)
python OLHD.py               # DOE 100점 미리보기 + 갭 제약 위반 건수 확인
python OLHD_PLOT.py          # DOE 분포 시각화 (선택)
python fins.py                # 핀 배치 수식 단독 확인 (두께별 최대개수, 갭 표, 검산)
python ML.py                  # 변수 영향도 진단 (데이터 쌓인 후)
python finalize_campaign.py  # 종료 후 여분 데이터 잘라내기 (선택)
```

---

## 8. 검증 상태

### 코드 레벨 통합 테스트로 검증 완료

SolidWorks/AEDT 없이 가짜 CFD 결과로 DOE 30 + 적응샘플링 12회를 흉내 낸
스모크 테스트로 확인:

- 갭 제약: 후보 20만 개 decode → 위반 0건, 최소 갭 정확히 2.500mm
- `fin_gap` 열이 `fin_thick`/`fin_count`로 재계산한 값과 정확히 일치
- 종료판정: 그룹별로 단위(rel %, abs LPM)가 섞여도 정상 판정, 절대오차
  그룹이 실제로 `|pred−실측|` 최댓값과 일치
- `finalize_campaign.py` 재판정 결과가 `ML.is_done()` 판정과 일치
- 모든 제안점이 정수 `fin_count`, 갭 제약, 고정 파라미터 포함 조건을 만족

발견/수정한 버그: `decode()`에서 반올림 순서가 잘못돼(두께 반올림 전에 허용
개수를 계산) 경계 근처 조합이 제약을 미세하게 위반하던 문제 — 2절 (4)절 참고.

### 미검증 — 실제 SolidWorks/Icepak 연동

`pythoncom`/`win32com`(SolidWorks COM) 및 `ansys.aedt.core`(AEDT)는 Windows
전용이라 이 환경에서 실행할 수 없다. 코드 구문·모듈 간 데이터 흐름은
확인했으나, 실제 형상 리빌드·메싱·해석은 **아직 한 번도 통과시킨 적이 없음**.
4절 체크리스트(핀뱅크 길이, 유로 깊이, 측정면 좌표, 메시 크기, 판재 부피
상수)를 실물과 대조하고, 첫 idx를 돌릴 때 로그 값(차압/CV/유량/중량)이
물리적으로 타당한지 눈으로 확인할 것.
