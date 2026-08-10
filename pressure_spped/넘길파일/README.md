# 냉각판 V2 — 유로 7변수 최적화 (내부망 반입용)

V1(각도·유로두께 2변수) 캠페인 코드를 **유로 7변수**로 재작성한 버전.
이 폴더 전체를 내부망으로 복사해서 사용.

---

## 1. 설계변수 (7개)

| # | 변수명 (SolidWorks 글로벌 변수명과 동일해야 함) | 범위 | 단위 |
|---|---|---|---|
| 1 | `input_thick` | 15 ~ 35 | mm |
| 2 | `input_angle` | 90 ~ 150 | deg |
| 3 | `power_input_thick` | 10 ~ 40 | mm |
| 4 | `power_output_thick` | 15 ~ 40 | mm |
| 5 | `mid_thick` | 15 ~ 35 | mm |
| 6 | `mid_angle` | 90 ~ 140 | deg |
| 7 | `output_thick` | 15 ~ 35 | mm |

정의 위치: `OLHD.py`의 `PARAM_SPEC` **한 곳뿐**. 범위를 바꾸려면 여기만 수정하면
OLHD / ML / SolidWorks / result_parser가 전부 따라감.

---

## 2. V1 대비 무엇이 바뀌었나

### (1) 적응 샘플링: 격자 전수탐색 → Sobol 후보 샘플링 ★ 가장 중요

V1은 설계공간을 0.1단위 격자(301×251 = 75,551점)로 **전부 나열**해서 그 중
불확실성(σ) 최대점을 골랐음. 7차원에서는 같은 방식이면 후보 수가 천문학적이라
열거 자체가 불가능.

→ 매 회차 Sobol로 **32,768개 후보만 뽑아** σ를 평가하고 그 중 최대점을 선택.

### (2) 중복 제외: 정수 매칭 → 최소거리 기준

격자가 없어졌으므로 "이미 한 점"을 정확히 매칭할 수 없음.
→ 정규화 공간에서 기존 실험점과 거리 `MIN_DIST_NORM`(0.05) 미만이면 후보에서 제외.

### (3) 형상 미성립(리빌드 실패) 방어 ★ 신규

7변수 조합에서는 기하학적으로 성립 불가한 형상이 나올 수 있음.
V1에는 이 처리가 없어서 실패하면 캠페인 전체가 죽음.

→ 실패 시 `failed_v2.csv`에 기록하고 다음 점으로 진행.
→ DOE 진행은 "성공 수"가 아니라 **"시도 수"** 기준이라 같은 점 무한재시도 없음.
→ 실패점 근처는 이후 후보에서도 제외 (형상 미성립 가능성이 높은 영역이므로).
→ 연속 5회 실패 시 설정 문제로 보고 중단.

### (4) SolidWorks 변수명 불일치 감지 ★ 신규

V1의 `set_value`는 해당 이름의 수식을 못 찾아도 **조용히 넘어갔음**
→ 형상이 안 바뀐 채로 해석이 도는 사고가 가능한 구조였음.
→ V2는 없는 변수명이면 즉시 `KeyError`로 중단하고, 실제 존재하는 변수 목록을 출력.

### (5) 인터페이스 정리

- 파라미터를 7개 위치인자 대신 `dict`로 전달
- `result_parser.extract_and_save`가 튜플 대신 `dict` 반환 (목적함수 늘려도 호출부 안 깨짐)
- ML에 `current_idx()` 공개 함수 추가 (V1은 main에서 private `_load_results()`를 씀)

### (6) GPR 커널

- `length_scale` 7차원 ARD
- 상한 5.0 → **50.0**: 7변수 중 영향 없는 변수는 length_scale이 커지는 형태로
  드러나는데, 상한에 걸리면 "무관한 변수"를 식별할 수 없기 때문

### (7) 신규 진단 기능: `python ML.py`

학습된 ARD length_scale을 뽑아 **어떤 변수가 실제로 영향을 주는지** 출력.
7개 중 몇 개가 실제로 의미 있는지 보고, 다음 캠페인에서 변수를 줄일 근거로 사용.

```
=== 변수 영향도 (데이터 40점 기준) ===
[pressure_drop] length_scale (작을수록 영향 큼)
         input_thick:    1.403  ##############
         input_angle:   50.000  #      ← 상한 = 사실상 영향 없음
```

---

## 3. 파일 구성

| 파일 | V1 대비 | 설명 |
|---|---|---|
| `OLHD.py` | 재작성 | 7변수 LHD + 변수 정의(PARAM_SPEC) 단일 출처 |
| `ML.py` | 재작성 | GPR + Sobol 적응샘플링 + 자동종료 + 실패기록 + 영향도진단 |
| `Solidworks.py` | 재작성 | 글로벌 변수 7개 일괄 set + 변수명 검증 |
| `result_parser.py` | 수정 | summary 컬럼 7변수화, dict 반환 |
| `main.py` | 재작성 | dict 전달 + 실패 시 skip 로직 |
| `icepak.py` | 경로만 수정 | 로직은 V1 그대로, 하드코딩 경로만 `paths.py` 참조로 변경 (4절 확인사항 참고) |
| `paths.py` | 신규 | 작업폴더 경로 전부 이 파일 한 곳에서 관리 |

### 작업폴더 / 경로

작업폴더: `E:\Thermal_Anlaysis\Liquid_plate\260810` (AEDT / Code / Result / Solidworks 하위폴더)
모든 경로는 **`paths.py` 한 곳에서만** 정의함 — 폴더 구조 바뀌면 여기만 수정.

| 상수 | 실제 경로 | 용도 |
|---|---|---|
| `PART_PATH` | `...\Solidworks\plate_base.SLDPRT` | 형상 파트 |
| `ASM_PATH` | `...\Solidworks\flowpath.SLDASM` | 어셈블리 |
| `STEP_DIR` | `...\Solidworks\Step\` | 실험점별 STEP 저장 |
| `AEDT_PROJ_PATH` | `...\AEDT\thermal_test` | Icepak 프로젝트 |
| `ICEPAK_RESULT_DIR` | `...\Result\` | Icepak 원본 CSV (`result_000.csv` 등) |
| `RESULTS_PATH` | `...\Result\results_v2.csv` | 실험 결과 + 예측값 (V1과 분리) |
| `SUMMARY_PATH` | `...\Result\summary_v2.csv` | 요약 |
| `FAILED_PATH` | `...\Result\failed_v2.csv` | 형상 미성립 등 실패점 |

> `Code` 폴더는 이 `.py` 파일들을 두는 곳 — 경로 상수는 아니고 실행 위치.

> ⚠ **`results_v2.csv` 삭제 금지.** STEP 파일명이 V1처럼 파라미터값이 아니라
> `flowpath_000.STEP`처럼 idx 기준이라(7개를 다 넣으면 경로가 너무 길어짐),
> **형상 ↔ 파라미터 대응은 이 CSV가 유일한 기록**임.

---

## 4. 반입 전 확인 필요 ⚠

### (1) 각도 변수 단위
`input_angle`, `mid_angle`을 mm로 주셨는데 값(90~150)으로 보아 **deg**로 간주하고 작성함.
맞는지 확인 필요.

### (2) SolidWorks 글로벌 변수명
V1은 한글(`각도`, `유로두께`)이었는데 V2는 영문명으로 작성함.
**Equation Manager의 실제 변수명과 철자가 정확히 일치**해야 함.
(불일치 시 첫 실행에서 바로 KeyError로 알려주므로 조용히 잘못 도는 일은 없음)

### (3) `icepak.py`의 하드코딩 좌표 ★ 중요
V1 형상 기준으로 고정된 값들이 있음. **V2에서 판 외곽/핀뱅크 위치가 바뀌면 깨짐.**

| 위치 | 값 | 의미 |
|---|---|---|
| `icepak.py:247` | `face.center[2] - 18.5` | Fan/Opening 면을 z=18.5 평면에서 탐지 |
| `icepak.py:629~633` | `x=-168.5, y_start=19.0, pitch 6.5` | 레인 속도 측정시트 30장 위치 |

→ 7변수가 **핀뱅크 입구 위치나 판 두께를 바꾸는지** 확인 필요.
   바꾼다면 이 좌표들도 파라미터 함수로 만들어야 함.

### (4) 초기 DOE 점 수 = 70
`10 × 변수수` 경험칙 기준. 실행 1회당 SolidWorks 리빌드 + Icepak 풀 해석이므로
**시간 예산 확인 필요**. 줄이려면 `ML.py`의 `N_DOE` 수정.

### (5) 목적함수 — 미확정
현재는 V1과 동일하게 `pressure_drop` + `vel_cv` 2개로 **임시 설정**.
`ML.py`의 `OBJECTIVES` 리스트만 고치면 나머지 코드는 그대로 동작하게 만들어둠.
→ 별도 논의 필요.

---

## 5. 실행

```bash
python main.py        # 캠페인 실행 (종료조건 만족까지 자동 반복)
python OLHD.py        # DOE 70점 미리보기
python ML.py          # 변수 영향도 진단 (데이터 쌓인 후)
```

---

## 6. 검증 상태

Windows COM(SolidWorks/Icepak) 없이 **ML 로직만 가짜 해석으로 검증 완료**:

- OLHD 70점: shape/범위/각 변수 10분위 분포 확인
- 전체 루프: DOE → 적응샘플링 진입 → 예측값 기록 → 자동종료 동작 확인
- 실패점 처리: 3점 실패시켜도 DOE가 밀리지 않고 중복 제안 없음 확인
- 영향도 진단: 무관한 변수를 실제로 걸러내는지 확인

**미검증**: SolidWorks COM 연동, Icepak 연동 (내부망에서만 가능)
