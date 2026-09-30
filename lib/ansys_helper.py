"""Ansys MAPDL 자동화 래퍼 (PyMAPDL). 단위는 SI(m, N, Pa, kg)."""
from ansys.mapdl.core import launch_mapdl


def start(**kwargs):
    mapdl = launch_mapdl(**kwargs)
    mapdl.clear()
    return mapdl


def set_isotropic_material(mapdl, mat_id, E, nu, density=None):
    mapdl.mp("EX", mat_id, E)
    mapdl.mp("PRXY", mat_id, nu)
    if density is not None:
        mapdl.mp("DENS", mat_id, density)


def fix_nodes_at(mapdl, axis, value, tol=1e-6):
    """axis('X'|'Y'|'Z') 좌표가 value인 절점을 완전 고정."""
    mapdl.nsel("S", "LOC", axis, value - tol, value + tol)
    mapdl.d("ALL", "ALL")
    mapdl.allsel()


def force_on_nodes_at(mapdl, axis, value, direction, total_force, tol=1e-6):
    """axis 좌표가 value인 절점들에 total_force를 균등 분배. direction: 'FX'|'FY'|'FZ'"""
    mapdl.nsel("S", "LOC", axis, value - tol, value + tol)
    n = mapdl.mesh.n_node
    if n == 0:
        mapdl.allsel()
        raise RuntimeError(f"{axis}={value} 위치에 절점이 없음")
    mapdl.f("ALL", direction, total_force / n)
    mapdl.allsel()


def solve_static(mapdl):
    mapdl.slashsolu()
    mapdl.antype("STATIC")
    mapdl.solve()
    mapdl.finish()


def get_max_results(mapdl):
    """(최대 변위 m, 최대 등가응력 Pa)"""
    mapdl.post1()
    mapdl.set(1, 1)
    disp = mapdl.post_processing.nodal_displacement("NORM").max()
    seqv = mapdl.post_processing.nodal_eqv_stress().max()
    return float(disp), float(seqv)
