# -*- coding: utf-8 -*-
"""
2D 평행평판 층류 해석해와 비교
  완전발달 압력기울기  dp/dx = 12 nu U / h^2       (운동학적 압력, m/s2)
  중심 최대속도        umax  = 1.5 U
"""
import glob

NU, U, H = 1e-5, 1.388889e-06 / (0.003 * 0.001), 0.003
exact_grad = 12 * NU * U / H**2
exact_umax = 1.5 * U

f = sorted(glob.glob("postProcessing/centerline/*/line_p_U.xy"))[-1]
d = [list(map(float, l.split())) for l in open(f)]
near = lambda x: min(d, key=lambda r: abs(r[0] - x))
a, b = near(0.20), near(0.28)          # 완전발달 구간
grad = -(b[1] - a[1]) / (b[0] - a[0])
umax = b[2]

e_g = (grad - exact_grad) / exact_grad * 100
e_u = (umax - exact_umax) / exact_umax * 100
print(f"압력기울기  CFD {grad:7.3f}  해석해 {exact_grad:7.3f}  오차 {e_g:+6.2f} %")
print(f"최대속도    CFD {umax:7.4f}  해석해 {exact_umax:7.4f}  오차 {e_u:+6.2f} %")
ok = abs(e_g) < 3 and abs(e_u) < 3
print("설치 검증:", "통과" if ok else "실패 -> 이 OpenFOAM으로 층류 압력강하를 믿으면 안 됨")
