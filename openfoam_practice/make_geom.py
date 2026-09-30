# -*- coding: utf-8 -*-
"""
[1단계] FreeCAD 매개변수 형상 생성

실행 (케이스 폴더 안에서):  freecadcmd /path/to/make_geom.py
입력:  ./params.json
출력:  ./coldplate.FCStd  (GUI로 열어 Spreadsheet 값을 바꿔볼 수 있음)
       ./solid.step, ./fluid.step  (단위 mm)

형상: 직사각형 판(L x W x H) 안을 x 방향으로 관통하는 직선 유로 1개.
모든 치수는 Spreadsheet의 alias에 수식으로 연결되어 있다.
(SolidWorks Equation Manager와 같은 역할)
"""
import json
import os
import sys

import FreeCAD as App

CWD = os.getcwd()
p = json.load(open(os.path.join(CWD, "params.json"), encoding="utf-8"))

# params.json 키 -> Spreadsheet alias
# (L, W, H는 리터·와트·헨리 단위 이름과 겹쳐 alias로 쓸 수 없어 plate_ 접두어를 붙임)
ALIAS = {"L": "plate_L", "W": "plate_W", "H": "plate_H",
         "ch_w": "ch_w", "ch_h": "ch_h", "ch_z": "ch_z"}
MIN_WALL = 0.5  # mm, 이보다 얇은 벽은 형상 실패로 처리


def fail(msg):
    print("GEOM_FAIL:", msg)
    sys.stdout.flush()
    os._exit(2)


# ---------- 사전 검사 (형상이 깨지는 조합 거르기) ----------
walls = {
    "bottom wall": p["ch_z"],
    "top wall": p["H"] - p["ch_z"] - p["ch_h"],
    "side wall": (p["W"] - p["ch_w"]) / 2,
}
for name, t in walls.items():
    if t < MIN_WALL:
        fail(f"{name} = {t:.3f} mm < {MIN_WALL} mm")

# ---------- Spreadsheet (설계변수) ----------
doc = App.newDocument("coldplate")
ss = doc.addObject("Spreadsheet::Sheet", "Spreadsheet")
for i, (k, alias) in enumerate(ALIAS.items(), start=1):
    ss.set(f"A{i}", alias)
    ss.set(f"B{i}", f"={p[k]} mm")
    ss.setAlias(f"B{i}", alias)
doc.recompute()

# ---------- 판 블록 ----------
block = doc.addObject("Part::Box", "PlateBlock")
block.setExpression("Length", "Spreadsheet.plate_L")
block.setExpression("Width", "Spreadsheet.plate_W")
block.setExpression("Height", "Spreadsheet.plate_H")

# ---------- 유체 영역 (유로) ----------
fluid = doc.addObject("Part::Box", "Fluid")
fluid.setExpression("Length", "Spreadsheet.plate_L")
fluid.setExpression("Width", "Spreadsheet.ch_w")
fluid.setExpression("Height", "Spreadsheet.ch_h")
fluid.setExpression(".Placement.Base.y", "(Spreadsheet.plate_W - Spreadsheet.ch_w) / 2")
fluid.setExpression(".Placement.Base.z", "Spreadsheet.ch_z")

# ---------- 고체 = 판 - 유로 ----------
plate = doc.addObject("Part::Cut", "Plate")
plate.Base = block
plate.Tool = fluid
doc.recompute()

# ---------- 검사 ----------
for obj in (plate, fluid):
    s = obj.Shape
    if s.isNull() or not s.isValid() or s.Volume <= 0:
        fail(f"{obj.Name} shape invalid")

print(f"solid volume = {plate.Shape.Volume:.1f} mm3")
print(f"fluid volume = {fluid.Shape.Volume:.1f} mm3")

# ---------- 저장 ----------
plate.Shape.exportStep(os.path.join(CWD, "solid.step"))
fluid.Shape.exportStep(os.path.join(CWD, "fluid.step"))
doc.saveAs(os.path.join(CWD, "coldplate.FCStd"))
print("GEOM_OK")
sys.stdout.flush()
os._exit(0)
