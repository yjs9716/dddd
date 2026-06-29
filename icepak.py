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

    result = 0.0
    return ipk, result
