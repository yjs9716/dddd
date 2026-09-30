# 프로젝트 개요
- SolidWorks, Ansys 작업을 Python으로 자동화하는 저장소
- Python 3.10+, Windows 전용 (SolidWorks COM 사용)
- 필요 패키지: pywin32 (SolidWorks), pyaedt (Ansys AEDT Icepak)

# 폴더 구조
- lib/sw_helper.py      : SolidWorks 래퍼 함수. SolidWorks 작업은 반드시 이 함수들을 사용한다.
- lib/icepak_helper.py  : Ansys Icepak 래퍼 함수. Icepak 작업은 반드시 이 함수들을 사용한다.
- docs/solidworks/      : SolidWorks API 규칙과 주의사항
- docs/ansys/           : Ansys AEDT Icepak 규칙과 주의사항
- examples/             : 검증된 예제 코드. 새 코드를 짤 때 가장 비슷한 예제를 먼저 읽고 따라 한다.

# 작업 방식
1. SolidWorks 작업 전에 docs/solidworks/overview.md를 먼저 읽는다.
2. Icepak 작업 전에 docs/ansys/icepak_overview.md를 먼저 읽는다.
3. lib/ 에 있는 함수로 가능한 작업은 직접 API를 호출하지 않고 함수를 사용한다.
4. lib/ 에 없는 API를 쓸 때는 추측하지 않는다. 모르면 사용자에게 API 이름을 확인해 달라고 요청한다.
5. 작업을 작은 단계로 나누고, 한 번에 한 파일씩 수정한다.

# 절대 규칙
- SolidWorks API의 길이 단위는 미터(m)다. mm 값은 반드시 /1000 해서 넣는다. (lib 함수는 mm를 받는다)
- SolidWorks API의 각도 단위는 라디안이다.
- Icepak 길이 단위는 mm로 통일한다. 값에는 단위를 붙인 문자열을 쓴다 ("2W", "25cel").
- SolidWorks → Icepak 형상 전달은 STEP 파일로 한다 (sw_helper.save_as → icepak_helper.import_cad).
- 원본 CAD 파일을 덮어쓰지 않는다. 결과는 항상 새 파일명으로 저장한다.
- 작업이 끝나면 SolidWorks 문서를 닫고, Icepak은 icepak_helper.close()로 AEDT를 종료한다.
