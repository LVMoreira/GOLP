#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal fort.10 reader for MULTI-IFE (ASCII 'binary') and quick plots.

Usage examples:
  python plot_multi.py fort.10 profile TI
  python plot_multi.py fort.10 trace TI --cell 50
  python plot_multi.py fort.10 profile TE    # electrons
"""

import argparse
from collections import defaultdict, namedtuple
import sys

import numpy as np
import matplotlib.pyplot as plt

Item = namedtuple("Item", ["name", "index"])

def read_int(f):
    line = f.readline()
    if not line:
        raise EOFError
    return int(line.strip())

def read_names(f, n):
    # n lines, each an 8-char label (possibly padded with spaces)
    names = []
    for _ in range(n):
        lbl = f.readline()
        if not lbl:
            raise EOFError("Unexpected EOF while reading names")
        names.append(lbl.rstrip("\n"))
    return names

def read_ints(f, n):
    vals = []
    for _ in range(n):
        line = f.readline()
        if not line:
            raise EOFError("Unexpected EOF while reading indices")
        vals.append(int(line.strip()))
    return vals

def read_floats(f, n):
    vals = []
    for _ in range(n):
        line = f.readline()
        if not line:
            raise EOFError("Unexpected EOF while reading values")
        vals.append(float(line.strip()))
    return vals

def group_structure(names, idxs):
    """
    Collapse repeated labels into variable groups.
    For scalars, idx == 0 and count == 1.
    For arrays, name repeats 'count' times and idx runs 1..count.
    Returns dict: name -> {"count": m, "is_array": bool, "indices": list}
    """
    groups = defaultdict(lambda: {"count": 0, "indices": []})
    for nm, ix in zip(names, idxs):
        key = nm.strip()  # strip padding
        g = groups[key]
        g["count"] += 1
        g["indices"].append(ix)
    for key, g in groups.items():
        g["is_array"] = (g["count"] > 1) or (g["indices"][0] != 0)
    return groups

def slice_values_into_groups(groups, values):
    """
    Given groups (order implied by concatenation of all items), split a flat 'values'
    list into per-variable arrays.
    Returns dict: name -> np.array (shape (count,))
    """
    out = {}
    pos = 0
    # We must follow the same concatenation order as in names/idxs
    for name in groups_order:
        g = groups[name]
        m = g["count"]
        arr = np.array(values[pos:pos+m], dtype=float)
        pos += m
        out[name] = arr
    return out

def read_section_header(f):
    nitems = read_int(f)
    names = read_names(f, nitems)
    idxs  = read_ints(f, nitems)
    # preserve the order in which variables appear
    groups = group_structure(names, idxs)
    order = []
    seen = set()
    for nm in names:
        key = nm.strip()
        if key not in seen:
            order.append(key)
            seen.add(key)
    return nitems, names, idxs, groups, order

def read_fort10(path):
    with open(path, "r") as f:
        # --- Static section
        n_s, names_s, idxs_s, groups_s, order_s = read_section_header(f)
        global groups_order
        groups_order = []  # used by slice_values_into_groups
        groups_order = [nm for nm in order_s]
        static_vals = read_floats(f, n_s)
        static = slice_values_into_groups(groups_s, static_vals)

        # --- Dynamic section (header)
        n_d, names_d, idxs_d, groups_d, order_d = read_section_header(f)
        # names and structure are fixed for all frames
        order_d = [nm for nm in order_d]
        # For slicing frames quickly, precompute how many values per frame:
        per_frame = n_d

        # Collect frames until EOF
        frames_flat = []
        while True:
            try:
                vals = read_floats(f, per_frame)
                frames_flat.append(vals)
            except EOFError:
                break
        frames_flat = np.array(frames_flat, dtype=float)  # shape (Nt, per_frame)
        Nt = frames_flat.shape[0]

        # Build dict name -> array over time.
        # First, compute counts per name
        gcounts = {nm: groups_d[nm]["count"] for nm in order_d}
        # offsets
        offsets = {}
        off = 0
        for nm in order_d:
            offsets[nm] = (off, off + gcounts[nm])
            off += gcounts[nm]

        dyn = {}
        for nm in order_d:
            a, b = offsets[nm]
            data = frames_flat[:, a:b]  # (Nt, count)
            # For scalars, squeeze to (Nt,)
            if gcounts[nm] == 1:
                dyn[nm] = data[:, 0]
            else:
                dyn[nm] = data  # (Nt, Nvar)
        # Also pass static + some helpful metadata
        meta = {
            "order_static": order_s,
            "order_dynamic": order_d,
            "counts_dynamic": gcounts,
            "Nt": Nt,
        }
        return static, dyn, meta

def plot_profile(dyn, meta, varname):
    var = varname.strip()
    if var not in dyn:
        raise KeyError(f"Variable '{var}' not in fort.10. Available: {list(dyn.keys())[:15]} ...")
    arr = dyn[var]
    t = dyn["TIME"]  # seconds
    # choose the last frame
    if arr.ndim == 1:
        # scalar series
        y = arr
        x = np.arange(arr.size)
        plt.plot(x, y)
        plt.xlabel("Frame")
        plt.ylabel(var)
        plt.title(f"{var} (scalar) vs frame")
    else:
        prof = arr[-1, :]   # last time, over space
        xcoord = dyn.get("XC", None)
        if isinstance(xcoord, np.ndarray) and xcoord.ndim == 2 and xcoord.shape[1] == prof.size:
            x = xcoord[-1, :]
            plt.plot(x, prof)
            plt.xlabel("x (cm)")
        else:
            plt.plot(np.arange(prof.size), prof)
            plt.xlabel("cell index")
        ylabel = f"{var} (eV)" if var in ("TE","TI","TR") else var
        plt.ylabel(ylabel)
        plt.title(f"{var} profile at t = {t[-1]:.3e} s")

def plot_trace(dyn, meta, varname, cell):
    var = varname.strip()
    if var not in dyn:
        raise KeyError(f"Variable '{var}' not in fort.10.")
    arr = dyn[var]
    t = dyn["TIME"]  # seconds
    if arr.ndim == 1:
        # scalar series
        plt.plot(t, arr)
        plt.xlabel("time (s)")
        plt.ylabel(var)
        plt.title(f"{var} vs time")
    else:
        if cell is None:
            cell = arr.shape[1] // 2
        if not (0 <= cell < arr.shape[1]):
            raise IndexError(f"Cell {cell} out of range [0..{arr.shape[1]-1}]")
        plt.plot(t, arr[:, cell])
        ylabel = f"{var} (eV)" if var in ("TE","TI","TR") else var
        plt.xlabel("time (s)")
        plt.ylabel(ylabel)
        plt.title(f"{var} at cell {cell} vs time")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fort10", help="path to fort.10")
    ap.add_argument("mode", choices=["profile","trace"], help="plot mode")
    ap.add_argument("var", help="variable name (e.g., TI, TE, R, X)")
    ap.add_argument("--cell", type=int, default=None, help="cell index for 'trace' mode")
    args = ap.parse_args()

    static, dyn, meta = read_fort10(args.fort10)

    plt.figure()
    if args.mode == "profile":
        plot_profile(dyn, meta, args.var)
    else:
        plot_trace(dyn, meta, args.var, args.cell)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
            print("ERROR:", e, file=sys.stderr)
            sys.exit(1)
