"""치수를 여러 값으로 바꿔 STEP 파일로 일괄 저장한다."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import sw_helper as sw_h

PART = r"C:\work\bracket.sldprt"
DIM = "D1@Boss-Extrude1"          # 돌출 깊이
VALUES_MM = [10, 20, 30]
OUT_DIR = r"C:\work\out"

sw = sw_h.connect()
model = sw_h.open_doc(sw, PART)
try:
    original = sw_h.get_dimension_mm(model, DIM)
    os.makedirs(OUT_DIR, exist_ok=True)
    for v in VALUES_MM:
        sw_h.set_dimension_mm(model, DIM, v)
        out = os.path.join(OUT_DIR, f"bracket_{v}mm.step")
        sw_h.save_as(model, out)
        print(f"{v}mm: mass={sw_h.get_mass_kg(model):.3f}kg -> {out}")
    sw_h.set_dimension_mm(model, DIM, original)  # 원래 값 복구 (원본은 저장하지 않음)
finally:
    sw_h.close_doc(sw, model)
