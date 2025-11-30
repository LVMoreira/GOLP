import numpy as np
import matplotlib.pyplot as plt

# --- Read fort.11 ---
filename = "fort.11"

# Skip header lines until we reach numeric data
data = np.loadtxt(filename, comments=('s', 'i'), skiprows=4)

# Columns from your sample:
# 1: i, 2: x, 3: v, 4: rho, 5: te, 6: ti, 7: depo
x = data[:, 1]     # position (cm)
rho = data[:, 2]   # density (g/cm^3)

# --- Plot ---
plt.figure()
plt.plot(x, rho, color='blue')
plt.xlabel("x (cm)")
plt.ylabel("Density (g/cm³)")
plt.title("Density profile from fort.11")
plt.grid(True)
plt.tight_layout()
plt.show()
