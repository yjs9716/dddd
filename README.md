# 수냉식 냉각판 열해석 자동화 최적화 파이프라인

## 프로젝트 개요

회사 내부망(폐쇄망) 환경에서 SolidWorks + ANSYS Icepak + Python ML을 연동하여  
유로 형상(각도, 두께)에 따른 열해석을 자동화하고, GPR(가우시안 프로세스 회귀) 기반 베이지안 최적화로 최적 설계를 탐색하는 파이프라인.

내부망 컴퓨터는 외부망과 완전 차단되어 있으므로, **GitHub repo(yjs9716/dddd)를 외부망 코드 저장소로 활용**하고 수동으로 내부망에 복붙하는 방식으로 운용.

```
외부망 (Claude + GitHub)          내부망 (실제 해석 실행)
┌────────────────────────┐        ┌────────────────────────────┐
│  claude.ai 채팅        │        │  SolidWorks (모델 업데이트) │
│  코드 작성/검토        │ ──수동──▶  ANSYS Icepak (열해석)     │
│  github.com/yjs9716   │  복붙   │  Python (ML 최적화)         │
│  /dddd  (코드 저장)   │        │  결과: summary.xlsx          │
└────────────────────────┘        └────────────────────────────┘
```

---

## 파일 구조

```
dddd/
├── main.py            # 메인 루프 (SW → Icepak → ML 순차 실행)
├── Solidworks.py      # SolidWorks COM 자동화 (글로벌 변수 제어 + STEP 저장)
├── icepak.py          # ANSYS Icepak 연결 및 프로젝트 생성
├── ML.py              # 실험계획 + GPR 최적화 (현재 스텁, 구현 예정)
├── result_parser.py   # Icepak CSV 결과 파싱 → summary.xlsx 저장
└── README.md          # 본 문서
```

---

## 설계변수 (Design Variables)

| 변수 | 범위 | 단위 | SolidWorks 글로벌 변수명 |
|------|------|------|--------------------------|
| 유로 각도 | 0 ~ 30 | ° | `각도` |
| 유로 두께 | 15 ~ 40 | mm | `유로두께` |

---

## 최적화 목표 (Objectives)

| 목표 | 방향 | 설명 |
|------|------|------|
| 최대 온도 | 최소화 | 19개 채널 중 최대값 |
| 온도 표준편차 | 최소화 | 19개 채널 평균온도의 std (균일성 극대화) |
| 차압 | 최소화 | 입출구 압력 차이 |

---

## 해석 설정

### 유체: PAO 냉각수

| 물성 | 값 | 단위 |
|------|----|------|
| 열전도도 (k) | 0.142 | W/m·K |
| 밀도 (ρ) | 794 | kg/m³ |
| 비열 (Cp) | 2219 | J/kg·K |
| 동적점도 (μ) | 0.00990 | kg/m·s |
| 열팽창계수 (β) | 0.00083 | 1/K |
| **입구 온도** | **20** | **°C** |
| 유량 | 3 ~ 4 | LPM |

> **유동 체계**: 레이놀즈수 Re < 500 → 완전 층류 (Laminar), Pr ≈ 142

### Icepak 설정

| 항목 | 설정 |
|------|------|
| 해석 유형 | Steady State (정상상태) |
| 유동 모델 | Laminar |
| 외기 온도 | 43 °C |
| 반복 횟수 | ~150 iterations |
| Flow Regime | Laminar (강제 설정) |

---

## 파이프라인 흐름

```
[main.py 시작]
     │
     ├─ connect_sw()      → SolidWorks COM 연결 + 어셈블리 열기
     ├─ connect_aedt()    → ANSYS Desktop 실행 (non-graphical=False)
     │
     └─ [메인 루프: while not is_done()]
           │
           ├─ get_next_params()          → (angle, thickness) 반환
           │                               (초기: LHS+maxmin DOE / 이후: GPR 제안)
           │
           ├─ update_sw(angle, thickness) → SolidWorks 글로벌 변수 수정 + 리빌드 + 저장
           │
           ├─ export_step(angle, thickness) → STEP 파일 저장
           │                                  경로: E:\Thermal_Anlaysis\Step\flowpath_a{angle}_t{thickness}.STEP
           │
           ├─ run_icepak(step_file)       → 기존 프로젝트 닫기 → STEP import
           │                                → (사용자 스크립트 레코더 코드로 해석 실행)
           │                                → result_xxx.csv 생성
           │
           ├─ extract_and_save(idx, ...)  → CSV 파싱 → summary.xlsx 누적 저장
           │
           └─ update_ml(angle, thickness, results) → ML 모델 업데이트
```

---

## 결과 파일 구조

### Icepak CSV 출력 (`result_xxx.csv`)

```
행 1~5:  헤더/메타 정보 (skiprows=5로 건너뜀)
행 6~24: 채널 1~19 데이터
         I열 (인덱스 8): 최대 온도 (°C)
         J열 (인덱스 9): 평균 온도 (°C)
행 25:   차압 데이터
         J열 (인덱스 9): 압력 강하 (Pa)
```

### 누적 요약 (`summary.xlsx`)

```
columns: idx | angle | thickness | max_temp | temp_std | pressure_drop
```

---

## 실험계획법 (DOE) 전략

### 1단계: 초기 샘플링 (LHS + maxmin / OLHD)
- 샘플 수: 약 20개
- 설계 공간 균등 탐색
- `doe.py` 구현 예정

### 2단계: GPR 기반 베이지안 최적화
- Gaussian Process Regression으로 surrogate model 구축
- EI (Expected Improvement) 기반 다음 실험점 제안
- `ML.py`에 구현 예정

---

## 진행 현황

### 완료
- [x] SolidWorks 자동화 (`Solidworks.py`)
- [x] ANSYS Desktop 연결 및 프로젝트 생성 (`icepak.py` 골격)
- [x] 메인 루프 구조 (`main.py`)
- [x] CSV 결과 파싱 로직 (`result_parser.py`)

### 진행 중
- [ ] `icepak.py`: 스크립트 레코더 코드 삽입 (사용자 직접 입력 예정)
  - 재료 설정, 경계조건, Fan/Opening 박스 생성, solve 명령

### 미완성 (구현 예정)
- [ ] `doe.py`: LHS+maxmin 초기 실험계획 생성
- [ ] `ML.py`: results.csv 기반 진행 상태 관리, DOE→GPR 전환 로직
- [ ] `main.py`: while 루프 전환, result_parser 연동, idx 관리

---

## 경로 상수 (내부망 환경)

```
E:\Thermal_Anlaysis\
├── Solidworks\
│   ├── plate_base.SLDPRT   (부품 파일)
│   └── flowpath.SLDASM     (어셈블리 파일)
├── Aedt\
│   └── thermal_test        (Icepak 프로젝트)
├── Step\
│   └── flowpath_a{angle}_t{thickness}.STEP
├── Results\
│   └── result_{idx:03d}.csv
└── summary.xlsx             (누적 결과)
```

---

## 주의사항

1. **DRM 제약**: `summary.xlsx`는 `pandas`로 직접 읽고 써야 함. Excel로 열어서 저장 누르면 DRM 걸림.
2. **내부망 코드 반영**: GitHub에 올린 코드를 내부망 컴퓨터에 수동 복붙 필요.
3. **Icepak 재시작 시**: `run_icepak()`이 기존 프로젝트를 닫고 디스크 파일을 삭제 후 새로 생성함.
4. **SolidWorks COM**: `pythoncom.CoInitialize()` 필수, 어셈블리 열기 후 작업.
