# -*- coding: utf-8 -*-
"""
[5단계] 여러 설계점 자동 반복 (DOE 표 -> 결과 표)

사용법:  python sweep.py doe_example.csv --np 4

- CSV의 열 이름은 params.json 키와 같아야 한다. 없는 키는 params.json 기본값 사용.
- 케이스마다 결과를 sweep_results.csv에 바로 추가 저장 (중간에 멈춰도 이어서 가능).
- 이미 OK로 끝난 케이스는 건너뜀.
- 해석이 끝나면 용량을 줄이기 위해 격자와 필드는 지우고 로그와 결과만 남긴다.
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

from run_case import HERE, run

CLEAN = ["constant/polyMesh", "constant/fluid/polyMesh", "constant/solid/polyMesh",
         "coldplate.msh", "processor*", "[1-9]*"]


def done_cases(path):
    if not path.exists():
        return set()
    with open(path, newline="") as f:
        return {r["case"] for r in csv.DictReader(f) if r["status"] == "OK"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doe")
    ap.add_argument("--np", type=int, default=1)
    ap.add_argument("--keep", action="store_true", help="격자와 필드를 지우지 않음")
    a = ap.parse_args()

    base = json.load(open(HERE / "params.json", encoding="utf-8"))
    out_csv = HERE / "sweep_results.csv"
    skip = done_cases(out_csv)

    with open(a.doe, newline="") as f:
        rows = list(csv.DictReader(f))

    for i, row in enumerate(rows):
        name = f"case_{i:03d}"
        if name in skip:
            print(f"== {name}: 이미 완료, 건너뜀")
            continue
        p = dict(base, **{k: float(v) for k, v in row.items()})
        case = HERE / "runs" / name
        case.mkdir(parents=True, exist_ok=True)
        pfile = case.parent / f"{name}.params.json"
        json.dump(p, open(pfile, "w"), indent=2)

        print(f"== {name}: {row}")
        res = run(pfile, case, a.np)

        if res["status"] == "OK" and not a.keep:
            for pat in CLEAN:
                for x in case.glob(pat):
                    shutil.rmtree(x) if x.is_dir() else x.unlink()

        rec = {"case": name, **row, **{k: v for k, v in res.items() if k != "case"}}
        new = not out_csv.exists()
        with open(out_csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rec.keys()))
            if new:
                w.writeheader()
            w.writerow(rec)


if __name__ == "__main__":
    sys.exit(main())
