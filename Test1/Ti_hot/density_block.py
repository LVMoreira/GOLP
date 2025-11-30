#!/usr/bin/env python3
"""
Auto-detect and plot density profile ρ(x) from MULTI fort.10.

Supports two formats:
  A) Classic fort.10 (static + dynamic sections with packed 8-char names)
  B) Block ASCII style (lines like: "step= ... time= ...", header "i x v rho te ti depo", then rows)

Usage:
  python3 multi_plot_auto.py --file fort.10 --time_ps 10    --xunit cm --out rho_10ps.pdf
  python3 multi_plot_auto.py --file fort.10 --frame 0       --xunit cm --out rho_t0.pdf
Options:
  --smooth K   optional boxcar smoothing over K cells
"""

import argparse, re, io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"]  = 42

# ------------------------------
# Utilities
# ------------------------------

def unit_factor_to_um(xunit: str) -> float:
    xunit = (xunit or "").lower()
    if xunit in ("cm",): return 1e4
    if xunit in ("m","meter","meters"): return 1e6
    if xunit in ("um","µm","micron","microns"): return 1.0
    raise SystemExit(f"Unknown --xunit '{xunit}'. Use: cm | m | um")

def boxcar(y: np.ndarray, k: int) -> np.ndarray:
    if k is None or k <= 1: return y
    kernel = np.ones(int(k), dtype=float)/int(k)
    return np.convolve(y, kernel, mode="same")

# ------------------------------
# Format B: Block ASCII parser
# ------------------------------

BLOCK_START_RE = re.compile(r"\bstep\s*=\s*(\d+)\s+time\s*=\s*([Ee0-9\+\-\.]+)", re.IGNORECASE)
HEADER_RE = re.compile(r"\s*i\s+x\s+v\s+rho\s+te\s+ti\s+depo", re.IGNORECASE)

def parse_block_ascii(stream: io.TextIOBase):
    """
    Parse block-style fort.10 into list of blocks:
      {"step": int, "time_s": float, "data": np.ndarray (N,7)}
    """
    blocks, cur = [], None
    for raw in stream:
        m = BLOCK_START_RE.search(raw)
        if m:
            # flush previous block
            if cur and cur.get("rows"):
                cur["data"] = np.array(cur["rows"], dtype=float)
                cur.pop("rows")
                blocks.append(cur)
            cur = {"step": int(m.group(1)), "time_s": float(m.group(2)), "rows": []}
            continue
        if cur is None:
            continue
        if HEADER_RE.search(raw):
            # header line; ignore
            continue
        parts = raw.strip().split()
        if len(parts) == 7 and parts[0].lstrip("+-").replace(".","",1).isdigit() is False:
            # some files have i as integer; but we won't over-validate here
            pass
        if len(parts) == 7:
            try:
                row = [float(p) for p in parts]
                cur["rows"].append(row)
            except ValueError:
                pass
    if cur and cur.get("rows"):
        cur["data"] = np.array(cur["rows"], dtype=float)
        cur.pop("rows")
        blocks.append(cur)
    if not blocks:
        raise ValueError("No block-ascii data found")
    return blocks

def pick_block(blocks, frame=None, time_ps=None):
    if frame is not None:
        i = int(np.clip(int(frame), 0, len(blocks)-1))
        return blocks[i], i
    if time_ps is not None:
        target = float(time_ps) * 1e-12
        times = np.array([b["time_s"] for b in blocks])
        i = int(np.abs(times - target).argmin())
        return blocks[i], i
    return blocks[-1], len(blocks)-1

# ------------------------------
# Format A: Classic fort.10 parser (robust to compact/expanded headers)
# ------------------------------

def _read_exact_names(fp, nfields):
    names = []
    while len(names) < nfields:
        line = fp.readline()
        if not line: raise EOFError("EOF while reading names")
        chunks = [line[i:i+8] for i in range(0, len(line.rstrip("\n")), 8)]
        names.extend([c.strip() for c in chunks if c.strip()])
    return names[:nfields]

def _read_exact_ints(fp, nfields):
    vals = []
    while len(vals) < nfields:
        line = fp.readline()
        if not line: raise EOFError("EOF while reading indices")
        for tok in line.strip().replace(",", " ").split():
            vals.append(int(tok))
    return vals[:nfields]

def _read_section_header(fp):
    line = fp.readline()
    if not line: raise EOFError("EOF reading section count")
    n_tokens = int(line.strip().split()[0])
    names = _read_exact_names(fp, n_tokens)
    lens  = _read_exact_ints(fp, n_tokens)
    if len(names) != len(lens):
        raise ValueError("Names/indices mismatch")
    # Try expanded; else compact
    items, i, ok = [], 0, True
    while i < n_tokens:
        name, L = names[i], lens[i]
        if L == 0:
            items.append((name, 0)); i += 1
        else:
            j = i + L
            if j <= n_tokens and all(n == name for n in names[i:j]) and all(v == L for v in lens[i:j]):
                items.append((name, L)); i = j
            else:
                ok = False; break
    if not ok:
        items = [(n, L) for n, L in zip(names, lens)]
    total_values = sum(1 if L == 0 else L for _, L in items)
    return {"items": items, "total_values": total_values}

def _read_values(fp, nvals):
    vals = []
    while len(vals) < nvals:
        line = fp.readline()
        if not line: raise EOFError("EOF while reading values")
        vals.extend([float(t) for t in line.strip().split()])
    return vals[:nvals]

def _skip_static(fp):
    meta = _read_section_header(fp)
    _ = _read_values(fp, meta["total_values"])

def read_classic_fort10(path):
    with open(path, "r") as fp:
        _skip_static(fp)
        dyn = _read_section_header(fp)
        rec_n = dyn["total_values"]
        items = dyn["items"]
        data = {name: [] for name,_ in items}
        while True:
            pos = fp.tell()
            line = fp.readline()
            if not line: break
            fp.seek(pos)
            try:
                vals = _read_values(fp, rec_n)
            except EOFError:
                break
            cur = 0
            for name, L in items:
                if L == 0:
                    data[name].append(vals[cur]); cur += 1
                else:
                    data[name].append(vals[cur:cur+L]); cur += L
    out = {}
    for k, seq in data.items():
        arr = np.array(seq, dtype=float)
        out[k] = arr if arr.ndim > 1 else arr.astype(float)
    return out  # expects keys TIME (s), R (Nt,N), XC (Nt,N)

# ------------------------------
# Auto-detect + plot
# ------------------------------

def is_block_ascii_head(sample: str) -> bool:
    return ("step=" in sample.lower() and "time=" in sample.lower()) or ("ascii_ouput" in sample.lower())

def main():
    ap = argparse.ArgumentParser(description="Plot ρ(x) at one time from fort.10 (auto-detect format).")
    ap.add_argument("--file","-f", default="fort.10")
    ap.add_argument("--time_ps", type=float, help="Pick nearest time (ps)")
    ap.add_argument("--frame", type=int, help="Pick by frame/block index (0-based)")
    ap.add_argument("--xunit", default="cm", help="x units in your file: cm | m | um (default cm)")
    ap.add_argument("--out","-o", default="density_profile.pdf")
    ap.add_argument("--smooth", type=int, default=1, help="Boxcar smooth over K cells")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    # Peek at the file to choose parser
    with open(args.file, "r") as f:
        sample = f.read(4096)

    if is_block_ascii_head(sample):
        # -------- Block ASCII fort.10 --------
        with open(args.file, "r") as f:
            blocks = parse_block_ascii(f)
        blk, idx = pick_block(blocks, frame=args.frame, time_ps=args.time_ps)
        data = blk["data"]  # columns: i x v rho te ti depo
        if data.shape[1] < 4:
            raise SystemExit("Expected at least 7 columns: i x v rho te ti depo.")
        x = data[:,1]
        rho = data[:,3]
        t_ps = blk["time_s"] * 1e12
        x_um = x * unit_factor_to_um(args.xunit)
    else:
        # -------- Classic fort.10 --------
        dyn = read_classic_fort10(args.file)
        for k in ("TIME","R","XC"):
            if k not in dyn:
                raise SystemExit(f"Missing '{k}' in dynamic section; file may be a different format.")
        t  = np.asarray(dyn["TIME"])   # s
        R  = np.asarray(dyn["R"])      # (Nt,N) g/cc
        XC = np.asarray(dyn["XC"])     # (Nt,N) cm
        Nt, N = R.shape
        if args.frame is not None:
            idx = int(np.clip(args.frame, 0, Nt-1))
        elif args.time_ps is not None:
            target = args.time_ps*1e-12
            idx = int(np.abs(t - target).argmin())
        else:
            idx = Nt-1
        x_um = XC[idx] * 1e4  # cm -> μm (classic)
        rho  = R[idx]
        t_ps = t[idx] * 1e12

    # Sort and optionally smooth
    order = np.argsort(x_um)
    x_um = x_um[order]
    rho  = rho[order]
    rho  = boxcar(rho, args.smooth)

    # Plot
    plt.figure()
    plt.plot(x_um, rho, lw=1.8)
    plt.xlabel("distance [μm]")
    plt.ylabel("density [g/cc]")
    title = args.title or f"ρ(x) at t ≈ {t_ps:.3g} ps"
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Wrote {args.out}  | frame={idx}  t≈{t_ps:.3g} ps")

if __name__ == "__main__":
    main()

