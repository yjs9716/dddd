"""Ansys AEDT Icepak 자동화 래퍼 (PyAEDT). 길이 인자는 mm."""
try:
    from ansys.aedt.core import Icepak
except ImportError:  # 구버전 PyAEDT
    from pyaedt import Icepak


def start(project=None, design="IcepakDesign", version=None, non_graphical=False):
    ipk = Icepak(
        project=project,
        design=design,
        version=version,
        non_graphical=non_graphical,
        new_desktop=True,
    )
    ipk.modeler.model_units = "mm"
    return ipk


def add_box(ipk, name, origin_mm, size_mm, material):
    return ipk.modeler.create_box(
        origin=list(origin_mm), sizes=list(size_mm), name=name, material=material
    )


def import_cad(ipk, path):
    ipk.modeler.import_3d_cad(path)
    return ipk.modeler.object_names


def set_heat_source(ipk, name, power):
    return ipk.create_source_block(name, power, assign_material=False)


def open_region_faces(ipk):
    return ipk.assign_openings(ipk.modeler["Region"].faces)


def add_temp_monitor(ipk, name):
    return ipk.monitor.assign_point_monitor_in_object(name, monitor_quantity="Temperature")


def set_mesh_resolution(ipk, level=3):
    region = ipk.mesh.global_mesh_region
    region.manual_settings = False
    region.settings["MeshRegionResolution"] = level
    region.update()


def solve(ipk, max_iter=100, cores=4, setup_name="Setup1"):
    setup = ipk.create_setup(setup_name)
    setup.props["Convergence Criteria - Max Iterations"] = max_iter
    setup.update()
    ipk.analyze_setup(setup.name, cores=cores)
    return setup


def get_max_temp(ipk, obj_name, setup_name="Setup1"):
    value = ipk.post.get_scalar_field_value(
        "Temperature",
        scalar_function="Maximum",
        solution=f"{setup_name} : SteadyState",
        object_name=obj_name,
    )
    return float(value)


def close(ipk, save_path=None):
    if save_path:
        ipk.save_project(save_path)
    ipk.release_desktop(close_projects=True, close_desktop=True)
