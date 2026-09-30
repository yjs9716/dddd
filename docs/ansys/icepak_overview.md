# Ansys AEDT Icepak (PyAEDT) 요약

## 설치 / 연결
```bash
pip install pyaedt
```
```python
from ansys.aedt.core import Icepak      # PyAEDT 0.9 이상
# from pyaedt import Icepak             # 구버전
```
- 이 저장소에서는 `lib.icepak_helper.start()`를 사용한다.
- AEDT가 설치된 PC에서만 동작한다. `version`은 설치된 AEDT 버전과 맞춘다 (예: "2024.2").

## 핵심 개념
- `ipk` (Icepak): 프로젝트/디자인 하나. 모든 작업의 시작점.
- `ipk.modeler`: 형상 생성, CAD 가져오기, 객체 조회 (`ipk.modeler["chip"]`)
- `ipk.mesh`: 메쉬 설정
- `ipk.monitor`: 온도 모니터 포인트
- `ipk.post`: 결과 추출
- `ipk["변수명"] = "2W"`: 디자인 변수. 값에는 반드시 단위를 문자열로 붙인다.

## 해석 순서 (반드시 이 순서)
1. 단위 설정: `ipk.modeler.model_units = "mm"`
2. 형상: 박스 생성 또는 STEP 가져오기
3. 재료 지정
4. 발열원 지정 (`create_source_block`)
5. 경계조건: 기본 `Region`의 면에 개구부(opening) 지정
6. 모니터 포인트
7. 메쉬 설정
8. 셋업 생성 → 해석 → 결과 추출
9. `ipk.save_project()` → `ipk.release_desktop()`

## 반드시 지킬 규칙
1. **PyAEDT는 버전마다 인자 이름이 자주 바뀐다.** (예: `position` → `origin`, `dimensions_list` → `sizes`)
   `TypeError: unexpected keyword argument` 에러가 나면 `help(함수)`로 현재 인자 이름을 확인한다. 추측하지 않는다.
2. 값에는 단위를 붙인 문자열을 쓴다: `"2W"`, `"25cel"`, `"1m_per_sec"`.
3. 새 Icepak 디자인에는 공기 영역 `Region`이 자동으로 있다. 새로 만들지 않는다.
4. 작업이 끝나면 반드시 `ipk.release_desktop()`을 호출한다. 안 하면 AEDT 프로세스와 라이선스가 남는다.
5. 원본 `.aedt` 파일을 덮어쓰지 않는다. `save_project(새경로)`로 저장한다.

## 자주 쓰는 재료 이름 (AEDT 기본 라이브러리)
- `"Al-Extruded"` (방열판), `"copper"`, `"FR-4"` (PCB), `"Ceramic_material"` (칩)

## lib/icepak_helper.py 함수 목록
| 함수 | 설명 |
|---|---|
| `start(project, design, version, non_graphical)` | AEDT 실행 + Icepak 디자인 열기/생성 |
| `add_box(ipk, name, origin_mm, size_mm, material)` | 박스 생성 |
| `import_cad(ipk, path)` | STEP 등 CAD 가져오기 (SolidWorks에서 내보낸 파일) |
| `set_heat_source(ipk, name, power)` | 객체를 발열원으로 지정. power 예: "2W" 또는 변수명 |
| `open_region_faces(ipk)` | Region 전체 면을 개구부(자연대류 환경)로 지정 |
| `add_temp_monitor(ipk, name)` | 객체 온도 모니터 |
| `set_mesh_resolution(ipk, level)` | 전체 메쉬 해상도 (1 거침 ~ 5 조밀) |
| `solve(ipk, max_iter, cores)` | 정상상태 셋업 생성 후 해석 |
| `get_max_temp(ipk, obj_name)` | 객체 최고 온도 (cel) |
| `close(ipk, save_path)` | 저장 후 AEDT 종료 |

## 예제
- `examples/icepak_chip_heatsink.py`: 칩 + 방열판 모델을 만들고 발열량별 최고 온도 비교
