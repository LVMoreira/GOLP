import sys
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIG ---
filename = "fort.11"
steps_to_plot = [31, 81, 183, 193]


def read_step_data(filename, step):
    time = None
    rows = []
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        step_r = None
        for line in f:
            s = line.strip()
            if not s:
                if rows: break
                continue
            parts = s.split()
            if len(parts) == 4:
                time = parts[3]
                step_r = int(parts[1])
            elif step_r is not None:
                if step_r != step:
                    continue
            try:
                nums = [float(p) for p in parts]
                if len(nums) < 6: continue
                if step_r == step:
                    rows.append(nums)
            except ValueError:
                if rows: break
    if not rows:
        return None, None, None
    arr = np.array(rows)
# Columns: 0:i, 1:x, 2:v, 3:rho, 4:te, 5:ti, 6:depo
    x = arr[:, 1]
    y = arr[:, 5]
    return x, y, time

# --- PLOT MULTIPLE STEPS ---
plt.figure()
for step in steps_to_plot:
    x, y, time = read_step_data(filename, step)
    if x is None:
        print(f"Step {step} not found.")
        continue
    try:
        t_ps = round(float(time) * 1e12)
        time_label = f"{t_ps} ps"
    except:
        time_label = f"{time} s"
    plt.plot(x, y, label=f"{t_ps} ps")

plt.xlabel("x (µm)")
plt.ylabel("Ti (eV)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.minorticks_on()
plt.gca().get_xaxis().get_offset_text().set_visible(False)
plt.grid(True, which="minor", alpha=0.15)
plt.tight_layout()
plt.show()
