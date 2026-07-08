# pressure_spped — 차압 + 속도CV 2목적 캠페인

유로(각도/두께) 재최적화용. 목적함수를 **차압 + 핀뱅크 입구 속도CV**로 교체한 버전.
온도/온도편차는 목적함수에서 제외하고 **기록용으로만** 저장 (열해석 자체는 그대로 켜둠).

## 파일

| 파일 | 역할 |
|------|------|
| `main_ps.py` | 메인 루프 (main_final.py 기반, 부모 폴더 모듈 재사용) |
| `sheets.py` | 핀뱅크 입구에 V_inlet_01~30 비모델 시트 생성 |
| `postprocess.py` | 속도 CSV export + CV 계산, 온도/차압 CSV 파싱 |
| `ml_ps.py` | GPR 2모델(차압, CV) 불확실성 탐색 + 종료판정 (ML_final.py 기반) |

기존 루트 파일(`Solidworks.py`, `icepak_final.py`, `OLHD.py`)은 수정 없이 그대로 import.
결과는 `results_ps.csv`로 저장 — 기존 `results.csv`(34회 캠페인)와 분리.

## 실행 전 확인 (게이트)

1. **CV 노이즈 플로어 미확정**: (40,30) 반복 실행으로 CV 23.7%가 재현되는지 확인 전까지
   "CV가 목적함수로 유효하다"는 미확정. 수동 3점 결과: (20,0)=21.82, (30,30)=21.73, (40,30)=23.71
2. **모델 단위 mm 확인**: `sheets.py` 좌표는 mm 기준. Modeler > Units가 m면 어긋남
3. **Speed 수량 이름**: `postprocess.py`의 Fields Summary가 `"Speed"`를 씀.
   수동 측정 때 GUI에서 쓴 수량과 같은지 확인 (다르면 해당 문자열 교체)
4. **MEAN_COL 확인**: 첫 실행 후 `speed_000.csv`를 열어 평균값 열이 인덱스 9(J열)가 맞는지 확인
5. **PAO 물성 온도의존 여부**: 재질카드가 상수면 flow-only 전환 가능(추후 경량화),
   온도의존이면 열해석 유지 필수. 현재 코드는 열해석 유지라 어느 쪽이든 안전

## 시트 생성 타이밍

시트는 NonModel이라 Solve 후 생성해도 결과에 영향 없음 (수동 검증 때와 동일한 순서).
`run_icepak()`이 온도/차압 export까지 끝낸 뒤 → 시트 생성 → 속도 export 순서.
`EditFieldsSummarySetting`은 설정을 통째로 교체하므로 이 순서를 바꾸면 안 됨.
