# -*- coding: utf-8 -*-
"""
설계점 하나를 끝까지 실행하는 드라이버
  FreeCAD(형상) -> Gmsh(격자) -> OpenFOAM(해석) -> 후처리

사용법:
  python run_case.py                              # params.json, runs/case_000
  python run_case.py --params my.json --out runs/case_007 --np 4

환경 변수:
  FREECADCMD : freecadcmd 실행 파일 경로 (기본값 "freecadcmd")
  OpenFOAM 환경은 미리 로드해 둘 것 (source .../etc/bashrc)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREECADCMD = os.environ.get("FREECADCMD", "freecadcmd")


def write_case_params(p, case):
    """params.json -> constant/caseParams (OpenFOAM 경계조건에서 #include로 읽음)"""
    flow = p["flow_Lpm"] / 1000.0 / 60.0  # L/min -> m3/s
    text = (
        "// run_case.py가 params.json에서 자동 생성\n"
        f"flowRate    {flow:.6e};   // m3/s ({p['flow_Lpm']} L/min)\n"
        f"T_in        {p['T_in_K']};         // K\n"
        f"Q_heater    {p['Q_heater_W']};          // W\n"
    )
    (case / "constant" / "caseParams").write_text(text, encoding="utf-8")


def step(name, cmd, case, timeout, env=None):
    log = case / f"run.{name}.log"   # Allrun이 지우는 log.* 와 겹치지 않게
    print(f"[{name}] ...", end=" ", flush=True)
    with open(log, "w") as f:
        try:
            rc = subprocess.run(cmd, cwd=case, stdout=f, stderr=subprocess.STDOUT,
                                timeout=timeout, env=env).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    print("OK" if rc == 0 else f"FAIL ({rc}) -> {log}")
    return rc == 0


def run(params_path, out, np_=1):
    p = json.load(open(params_path, encoding="utf-8"))
    case = Path(out).resolve()
    if case.exists():
        shutil.rmtree(case)
    shutil.copytree(HERE / "case_template", case)
    json.dump(p, open(case / "params.json", "w"), indent=2)
    write_case_params(p, case)

    env = dict(os.environ, NP=str(np_))
    ok = (step("geom", [FREECADCMD, str(HERE / "make_geom.py")], case, 600)
          and step("mesh", [sys.executable, str(HERE / "make_mesh.py")], case, 1800)
          and step("solve", ["bash", "Allrun"], case, 6 * 3600, env))
    if not ok:
        return {"status": "FAIL", "case": str(case)}

    sys.path.insert(0, str(HERE))
    import post
    res = post.summarize(case)
    res["status"] = "OK"
    json.dump(res, open(case / "result.json", "w"), indent=2)
    post.report(res)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=str(HERE / "params.json"))
    ap.add_argument("--out", default=str(HERE / "runs" / "case_000"))
    ap.add_argument("--np", type=int, default=1)
    a = ap.parse_args()
    r = run(a.params, a.out, a.np)
    sys.exit(0 if r["status"] == "OK" else 1)
