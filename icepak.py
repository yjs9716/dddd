from ansys.aedt.core import Desktop, Icepak
import os, shutil

PROJ_PATH = r"E:\Thermal_Anlaysis\Aedt\thermal_test"

def connect_aedt():
    desktop = Desktop(
        version="2025.1",
        non_graphical=False,
        new_desktop=True,
        close_on_exit=False,        # ← 생성 인자로 전달
    )
    print("AEDT 켜짐")
    return desktop, None

def run_icepak(desktop, ipk, step_file):
    # 기존 프로젝트 닫기 (AEDT는 유지)
    if ipk is not None:
        oDesktop = ipk.odesktop
        proj_name = ipk.project_name
        ipk = None
        oDesktop.CloseProject(proj_name)

    # 디스크 파일 삭제
    if os.path.exists(PROJ_PATH + ".aedt"):
        os.remove(PROJ_PATH + ".aedt")
    if os.path.exists(PROJ_PATH + ".aedtresults"):
        shutil.rmtree(PROJ_PATH + ".aedtresults")

    # 새 프로젝트 생성 (close_on_exit=False 필수)
    ipk = Icepak(
        project=PROJ_PATH,
        new_desktop=False,
        close_on_exit=False,        # ← 이것도 인자로
    )
    print("새 프로젝트 생성:", ipk.project_name)

    ipk.modeler.import_3d_cad(step_file)
    print("임포트 완료:", step_file)

    # ===== TODO: 아래 객체/면 이름은 실제 모델 트리에서 확인 후 교체 =====
    SOLID_OBJECT = "flowpath_1"     # CAD import 후 생성되는 솔리드 이름
    INLET_FACE   = "inlet"          # 입구 면 이름 (named selection)
    OUTLET_FACE  = "outlet"         # 출구 면 이름
    MATERIAL     = "Al-Extruded"    # Icepak material 라이브러리 내 이름
    INLET_FLOW_M3_S = 0.001         # 고정 BC: 입구 유량 [m3/s]
    OUTLET_PRESSURE_PA = 0          # 고정 BC: 출구 정압 [Pa]

    # 1) Material 지정
    ipk.assign_material(SOLID_OBJECT, MATERIAL)
    print("Material 지정 완료:", MATERIAL)

    # 2) Boundary condition 지정 (고정 BC, 매 iteration 동일)
    ipk.assign_velocity_free_opening(
        INLET_FACE,
        boundary_name="Inlet",
        flow_type="Mass Flow",
        flow_assignment=f"{INLET_FLOW_M3_S}kg_per_s",
    )
    ipk.assign_pressure_free_opening(
        OUTLET_FACE,
        boundary_name="Outlet",
        pressure_assignment=f"{OUTLET_PRESSURE_PA}Pa",
    )
    print("BC 지정 완료")

    # 3) Mesh / Setup 생성
    setup = ipk.create_setup(setupname="ThermalSetup")
    print("Setup 생성 완료:", setup.name)

    # 4) Solve
    ipk.analyze_setup(setup.name)
    print("해석 완료")

    # 5) 결과 추출: 최대 온도, 압력손실
    max_temp = ipk.post.get_scalar_field_value(
        quantity="Temperature", scalar_function="Maximum"
    )
    pressure_drop = ipk.post.get_scalar_field_value(
        quantity="Pressure", scalar_function="Delta"
    )

    # 6) 복합 목표값 계산 (가중합, 가중치는 TODO: 도메인 기준 확정 필요)
    W_TEMP = 0.5
    W_PRESSURE = 0.5
    result = W_TEMP * max_temp + W_PRESSURE * pressure_drop
    print(f"최대온도:{max_temp} 압력손실:{pressure_drop} 종합result:{result}")

    return ipk, result
