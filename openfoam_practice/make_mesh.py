# -*- coding: utf-8 -*-
"""
[2단계] Gmsh 영역 분할 격자 생성

실행 (케이스 폴더 안에서):  python /path/to/make_mesh.py
입력:  ./params.json, ./solid.step, ./fluid.step
출력:  ./coldplate.msh  (MSH 2.2 ASCII, 단위 m)

Physical Group 이름이 그대로 OpenFOAM 이름이 된다.
  체적: fluid, solid                 -> cellZone (splitMeshRegions로 영역 분리)
  면  : inlet, outlet, heater, solid_walls -> patch
  고체-유체 접촉면은 이름을 붙이지 않는다 (splitMeshRegions가 자동 생성).
"""
import json
import sys

import gmsh

p = json.load(open("params.json", encoding="utf-8"))
MM = 1e-3
L, W = p["L"] * MM, p["W"] * MM
A = p["heater_a"] * MM
EPS = 1e-6  # m, 좌표 비교 허용오차

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setString("Geometry.OCCTargetUnit", "M")  # STEP(mm) -> m
gmsh.model.add("coldplate")

solid_in = gmsh.model.occ.importShapes("solid.step")
fluid_in = gmsh.model.occ.importShapes("fluid.step")

# 발열 패드 자리: 판 밑면(z=0) 중앙의 정사각형. fragment로 밑면에 새겨 넣는다.
rect = gmsh.model.occ.addRectangle(L / 2 - A / 2, W / 2 - A / 2, 0, A, A)

# fragment: 고체-유체 접촉면을 공유(conformal)시키고 발열 패드 면을 분할
_, out_map = gmsh.model.occ.fragment(solid_in + fluid_in, [(2, rect)])
gmsh.model.occ.synchronize()

n_s, n_f = len(solid_in), len(fluid_in)
solid_vols = [t for m in out_map[:n_s] for d, t in m if d == 3]
fluid_vols = [t for m in out_map[n_s:n_s + n_f] for d, t in m if d == 3]
heater = [t for d, t in out_map[n_s + n_f] if d == 2]
if len(solid_vols) != 1 or len(fluid_vols) != 1 or not heater:
    print("MESH_FAIL: unexpected topology", solid_vols, fluid_vols, heater)
    sys.exit(2)


def faces_of(vol):
    return set(gmsh.model.getAdjacencies(3, vol)[1])


s_faces, f_faces = faces_of(solid_vols[0]), faces_of(fluid_vols[0])
interface = s_faces & f_faces


def on_plane_x(tag, x0):
    xmin, _, _, xmax, _, _ = gmsh.model.getBoundingBox(2, tag)
    return abs(xmin - x0) < EPS and abs(xmax - x0) < EPS


inlet = [t for t in f_faces - interface if on_plane_x(t, 0.0)]
outlet = [t for t in f_faces - interface if on_plane_x(t, L)]
solid_walls = sorted(s_faces - interface - set(heater))

if not inlet or not outlet or not interface:
    print("MESH_FAIL: inlet/outlet/interface not found")
    sys.exit(2)

gmsh.model.addPhysicalGroup(3, fluid_vols, name="fluid")
gmsh.model.addPhysicalGroup(3, solid_vols, name="solid")
gmsh.model.addPhysicalGroup(2, inlet, name="inlet")
gmsh.model.addPhysicalGroup(2, outlet, name="outlet")
gmsh.model.addPhysicalGroup(2, heater, name="heater")
gmsh.model.addPhysicalGroup(2, solid_walls, name="solid_walls")

# ---------- 격자 크기: 유로 벽(접촉면) 근처를 촘촘하게 ----------
h_min, h_max = p["mesh_min"] * MM, p["mesh_max"] * MM
f_dist = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(f_dist, "SurfacesList", sorted(interface))
f_thr = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(f_thr, "InField", f_dist)
gmsh.model.mesh.field.setNumber(f_thr, "SizeMin", h_min)
gmsh.model.mesh.field.setNumber(f_thr, "SizeMax", h_max)
gmsh.model.mesh.field.setNumber(f_thr, "DistMin", 1.0 * MM)
gmsh.model.mesh.field.setNumber(f_thr, "DistMax", 6.0 * MM)
gmsh.model.mesh.field.setAsBackgroundMesh(f_thr)

gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
gmsh.option.setNumber("Mesh.Optimize", 1)

gmsh.model.mesh.generate(3)

gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)  # gmshToFoam 호환
gmsh.option.setNumber("Mesh.Binary", 0)
gmsh.write("coldplate.msh")

n_tet = sum(len(t) for t in gmsh.model.mesh.getElements(3)[1])
print(f"MESH_OK: {n_tet} tetrahedra")
gmsh.finalize()
