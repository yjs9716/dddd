# SolidWorks API (Python + pywin32) 요약

## 연결
```python
import win32com.client
sw = win32com.client.Dispatch("SldWorks.Application")
sw.Visible = True
```
- 이 저장소에서는 `lib.sw_helper.connect()`를 사용한다.

## 핵심 개념
- `sw` (ISldWorks): 프로그램 자체. 문서 열기/닫기.
- `model` (IModelDoc2): 열린 문서(파트/어셈블리/도면). 대부분의 작업 대상.
- `model.Extension` (IModelDocExtension): 저장, 선택, 질량 특성 등 확장 기능.

## 문서 종류 상수
| 종류 | 값 | 확장자 |
|---|---|---|
| 파트 | 1 | .sldprt |
| 어셈블리 | 2 | .sldasm |
| 도면 | 3 | .slddrw |

## 반드시 지킬 규칙
1. **길이는 미터(m), 각도는 라디안.** 25mm → 0.025
2. **치수 이름 형식은 "치수명@피처명"** 이다. 예: `"D1@Sketch1"`, `"D1@Boss-Extrude1"`.
   한글 SolidWorks는 피처명이 한글일 수 있다. 예: `"D1@스케치1"`.
3. **치수를 바꾼 뒤에는 반드시 리빌드**한다 (`model.EditRebuild3()`).
4. **ByRef 인자**(errors, warnings 등)는 일반 변수로 넘기면 안 된다. `lib.sw_helper`의 `_byref_int()`를 사용한다.
5. 메서드 이름 끝의 숫자(`OpenDoc6`, `Save3`, `EditRebuild3`)는 버전이다. 숫자를 임의로 바꾸지 않는다.

## pywin32 주의사항
- 인자가 없는 일부 메서드가 속성처럼 노출되는 경우가 있다.
  `TypeError: 'bool' object is not callable` 같은 에러가 나면 괄호를 빼고 다시 시도한다.
  (`lib.sw_helper._call()`이 이 문제를 처리한다)
- SolidWorks가 설치된 Windows PC에서만 동작한다.

## lib/sw_helper.py 함수 목록
| 함수 | 설명 |
|---|---|
| `connect()` | SolidWorks 연결 |
| `open_doc(sw, path)` | 문서 열기 (확장자로 종류 자동 판별) |
| `get_dimension_mm(model, name)` | 치수 읽기 (mm) |
| `set_dimension_mm(model, name, value_mm)` | 치수 변경 (mm) + 리빌드 |
| `set_custom_property(model, name, value)` | 사용자 정의 속성 쓰기 |
| `get_mass_kg(model)` | 질량 (kg) |
| `save_as(model, path)` | 다른 이름으로 저장 (.sldprt, .step, .pdf 등 확장자로 형식 결정) |
| `close_doc(sw, model)` | 문서 닫기 |

## 예제
- `examples/sw_dimension_sweep.py`: 치수를 여러 값으로 바꿔 STEP 파일로 일괄 저장
