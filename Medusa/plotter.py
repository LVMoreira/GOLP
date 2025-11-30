import sys
import numpy as np
import matplotlib.pyplot as plt

#OPEN FILE
if len(sys.argv) < 2:
    filename = "Medusa/Med103_0d42e13Wcm2_5ps.txt"
else:
    filename = sys.argv[1]
time = None
step = 5
step_r = None

#ITERATE
rows = []
with open(filename, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        s = line.strip()
        if not s:
            if rows: break
            continue
        parts = s.split()
        try:
            nums = [float(p) for p in parts]
            rows.append(nums)
        except ValueError:
            if rows: break

if not rows:
    raise SystemExit(f"No numeric data found in {filename}")

#SORT DATA
arr = np.array(rows)
# Columns: 0:i, 1:x, 2:v, 3:rho, 4:te, 5:ti, 6:depo
x   = arr[:, 0]
rho = arr[:, 1]
print(rows)
print(arr)

#PLOT
title = f""
plt.plot(x, rho)
plt.xlabel("x (μm)")
plt.ylabel("ρ (g/cm³)")
if time is not None:
        title += "step = "+ str(step_r) + f"\nt =" + time + " s"
plt.title(title)
plt.grid(True, alpha=0.3)
plt.minorticks_on()                      
plt.grid(True, which="minor", alpha=0.15)
plt.tight_layout()
plt.show()
