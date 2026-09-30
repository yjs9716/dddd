# Ansys MAPDL (PyMAPDL) 요약

## 설치 / 연결
```bash
pip install ansys-mapdl-core
```
```python
from ansys.mapdl.core import launch_mapdl
mapdl = launch_mapdl()
```
- 이 저장소에서는 `lib.ansys_helper.start()`를 사용한다.

## 핵심 개념
- APDL 명령어는 대부분 **소문자 메서드**로 똑같이 존재한다.
  `ET,1,SOLID186` → `mapdl.et(1, "SOLID186")`
- 슬래시 명령어는 이름이 바뀐다: `/PREP7` → `mapdl.prep7()`, `/SOLU` → `mapdl.slashsolu()`, `/POST1` → `mapdl.post1()`
- 메서드로 없는 명령어는 `mapdl.run("명령어 문자열")`로 실행한다.

## 해석 순서 (반드시 이 순서)
1. `mapdl.prep7()` — 전처리: 요소 타입, 재료, 형상, 메쉬, 경계조건
2. `mapdl.slashsolu()` — 해석: `antype`, `solve()`
3. `mapdl.finish()`
4. `mapdl.post1()` — 후처리: 결과 추출

## 반드시 지킬 규칙
1. **단위는 SI(m, N, Pa, kg)로 통일**한다. MAPDL은 단위를 검사하지 않는다.
2. `nsel`, `esel` 등으로 선택한 뒤에는 **반드시 `mapdl.allsel()`로 선택을 복구**한다.
3. 결과는 `mapdl.post_processing`으로 읽는다.
   - 변위: `mapdl.post_processing.nodal_displacement("NORM")`
   - 등가응력: `mapdl.post_processing.nodal_eqv_stress()`
4. 작업이 끝나면 `mapdl.exit()`로 라이선스를 반납한다.

## lib/ansys_helper.py 함수 목록
| 함수 | 설명 |
|---|---|
| `start()` | MAPDL 실행 |
| `set_isotropic_material(mapdl, mat_id, E, nu, density)` | 등방성 재료 정의 |
| `fix_nodes_at(mapdl, axis, value)` | 좌표 axis=value 위치 절점 완전 고정 |
| `force_on_nodes_at(mapdl, axis, value, direction, total_force)` | 해당 위치 절점에 총 하중을 균등 분배 |
| `solve_static(mapdl)` | 정적 해석 실행 |
| `get_max_results(mapdl)` | 최대 변위(m), 최대 등가응력(Pa) 반환 |

## 예제
- `examples/ansys_cantilever.py`: 외팔보 정적 해석 후 최대 변위/응력 출력
