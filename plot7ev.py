import numpy as np
import matplotlib.pyplot as plt
import argparse

def read_fort(filename):
    data = []
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split()
            try:
                row = [float(x) for x in parts]
                data.append(row)
            except ValueError:
                continue
    return np.array(data)

def plot_columns(filename, xcol=1, ycol=4):
    data = read_fort(filename)
    x = data[:, xcol]
    y = data[:, ycol]

    plt.figure(figsize=(6,4))
    plt.plot(x, y, marker='o', linestyle='-')
    plt.xlabel(f"Column {xcol+1}")
    plt.ylabel(f"Column {ycol+1}")
    plt.title(f"{filename}: col {ycol+1} vs col {xcol+1}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot two columns from a fort.* file")
    parser.add_argument("file", help="fort.* file to plot (e.g., fort.11)")
    parser.add_argument("--xcol", type=int, default=1, help="X column index (0-based)")
    parser.add_argument("--ycol", type=int, default=4, help="Y column index (0-based)")
    args = parser.parse_args()

    plot_columns(args.file, xcol=args.xcol, ycol=args.ycol)
