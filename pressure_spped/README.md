# pressure_spped — 차압 + 속도CV 2목적 캠페인

유로(각도/두께) 재최적화. 목적함수를 **차압 + 핀뱅크 입구 속도CV**로 교체한 버전.
온도/온도편차는 목적함수에서 제외하고 **기록용으로만** 저장 (열해석은 그대로 켜둠).

**이 폴더 하나만 내부망에 통째로 복사하면 실행 가능** (루트 파일 의존 없음).

## 파일 (루트와 동일 구조)

| 파일 | 원본 대비 변경점 |
|------|------|
| `main.py` | run_icepak 반환값에 speed_path 추가, update_ml에 vel_cv 전달 |
| `icepak.py` | run_icepak 끝에 V_inlet_01~30 시트 생성(피치 6.5mm) + Speed export 추가 |
| `ML.py` | GPR 3모델 → **2모델(차압 log, 속도CV)**. 탐색·종료판정 모두 2개 기준 |
| `result_parser.py` | speed CSV 파싱 → CV(%) 계산 추가. 저장처: summary_ps.xlsx |
| `Solidworks.py` | 변경 없음 (루트 복사본) |
| `OLHD.py` | 변경 없음 (루트 복사본, seed=42 동일 → 기존 캠페인과 idx별 형상 동일) |

결과 파일: `results_ps.csv`, `summary_ps.xlsx`, `Results\speed_{idx:03d}.csv`
— 기존 34회 캠페인 산출물(results.csv, summary.xlsx)과 분리.

## CV 정의

레인 30개 평균유속의 모집단 표준편차(STDEV.P) / 평균 × 100 [%].
수동 3점 결과: (두께20,각도0)=21.82 / (30,30)=21.73 / (40,30)=23.71

## 실행 전 확인 (게이트)

1. **CV 노이즈 플로어**: (40,30) 반복 실행으로 23.7%가 재현되는지 미확인.
   재현 안 되면(노이즈면) 이 캠페인 무의미 → 먼저 확인할 것
2. **모델 단위 mm**: 시트 좌표는 mm 기준. Modeler > Units 확인
3. **Speed 수량 이름**: icepak.py의 Fields Summary가 `"Speed"` 사용.
   수동 측정 때 GUI에서 쓴 수량과 다르면 해당 문자열 교체
4. **speed CSV의 Mean 열**: 첫 실행 후 speed_000.csv 열어서 평균값이
   J열(인덱스 9)이 맞는지 확인 — 다르면 result_parser.py의 열 인덱스 수정
