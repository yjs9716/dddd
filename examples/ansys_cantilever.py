"""외팔보(1m x 0.1m x 0.1m 강재) 끝단 하중 정적 해석."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import ansys_helper as ah

mapdl = ah.start()
try:
    mapdl.prep7()
    mapdl.et(1, "SOLID186")
    ah.set_isotropic_material(mapdl, 1, E=210e9, nu=0.3, density=7850)
    mapdl.block(0, 1.0, 0, 0.1, 0, 0.1)
    mapdl.esize(0.02)
    mapdl.vmesh("ALL")

    ah.fix_nodes_at(mapdl, "X", 0.0)
    ah.force_on_nodes_at(mapdl, "X", 1.0, "FY", -1000.0)

    ah.solve_static(mapdl)
    disp, seqv = ah.get_max_results(mapdl)
    print(f"최대 변위: {disp * 1000:.3f} mm")
    print(f"최대 등가응력: {seqv / 1e6:.2f} MPa")
finally:
    mapdl.exit()
