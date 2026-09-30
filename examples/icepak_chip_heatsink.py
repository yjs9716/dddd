"""PCB 위 칩 + 방열판 모델을 만들고, 칩 발열량별 최고 온도를 비교한다."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import icepak_helper as ih

POWERS = ["1W", "2W", "5W"]
SAVE = r"C:\work\out\chip_heatsink.aedt"

ipk = ih.start(version="2024.2", non_graphical=True)
try:
    ih.add_box(ipk, "pcb", [0, 0, 0], [60, 60, 1.6], "FR-4")
    ih.add_box(ipk, "chip", [20, 20, 1.6], [20, 20, 2], "Ceramic_material")
    ih.add_box(ipk, "heatsink", [15, 15, 3.6], [30, 30, 10], "Al-Extruded")

    ipk["chip_power"] = POWERS[0]
    ih.set_heat_source(ipk, "chip", "chip_power")
    ih.open_region_faces(ipk)
    ih.add_temp_monitor(ipk, "chip")
    ih.set_mesh_resolution(ipk, 3)

    setup = None
    for p in POWERS:
        ipk["chip_power"] = p
        if setup is None:
            setup = ih.solve(ipk, max_iter=100)
        else:
            ipk.analyze_setup(setup.name)
        print(f"{p}: 칩 최고 온도 = {ih.get_max_temp(ipk, 'chip'):.1f} cel")
finally:
    ih.close(ipk, SAVE)
