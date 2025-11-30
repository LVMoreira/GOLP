
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt

# Optional nicer fonts in vector outputs
import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

# -----------------------------
# Robust fort.10 reader (ASCII)
# -----------------------------

def _read_exact_names(fp, nfields):
    """Read 8-char packed names across as many lines as needed until nfields collected."""
    names = []
    while len(names) < nfields:
        line = fp.readline()
        if not line:
            raise EOFError("EOF while reading names record")
        row = [line[i:i+8] for i in range(0, len(line.rstrip("\n")), 8)]
        row = [s.strip() for s in row if s.strip()]
        names.extend(row)
    return names[:nfields]

def _read_exact_ints(fp, nfields):
    """Read integers (0 or array lengths) across as many lines as needed until nfields collected."""
    vals = []
    while len(vals) < nfields:
        line = fp.readline()
        if not line:
            raise EOFError("EOF while reading indices record")
        for tok in line.strip().split():
            tok = tok.strip().rstrip(",")
            if tok:
                vals.append(int(tok))
    return vals[:nfields]

def _read_section_header(fp):
    """
    Read one fort.10 section header (static or dynamic).
    Returns meta dict with 'items' (list of (name, arr_len)) and 'total_values'.
    """
    n_elems_line = fp.readline()
    if not n_elems_line:
        raise EOFError("EOF reading section element count")
    n_elems = int(n_elems_line.strip().split()[0])

    # Names and lengths can wrap over multiple lines
    names_repeated = _read_exact_names(fp, n_elems)
    lens_repeated  = _read_exact_ints(fp, n_elems)

    if len(names_repeated) != len(lens_repeated):
        raise ValueError("Names/indices length mismatch in section header")

    # Compress consecutive repeats into variables: scalar => (name, 0), array => (name, L)
    items = []
    i = 0
    while i < n_elems:
        name = names_repeated[i]
        L = lens_repeated[i]
        if L == 0:
            items.append((name, 0))
            i += 1
        else:
            if i + L > n_elems:
                raise ValueError(f"Malformed header for {name}: run exceeds field count")
            if any(n != name for n in names_repeated[i:i+L]) or any(v != L for v in lens_repeated[i:i+L]):
                raise ValueError(f"Malformed array descriptor for {name}")
            items.append((name, L))
            i += L

    total_values = sum(1 if L == 0 else L for _, L in items)
    return {"items": items, "total_values": total_values}

def _read_values(fp, nvals):
    """Read nvals floats, across as many lines as necessary."""
    vals = []
    while len(vals) < nvals:
        line = fp.readline()
        if not line:
            raise EOFError("EOF while reading values")
        parts = line.strip().split()
        for tok in parts:
            vals.append(float(tok))
    return vals[:nvals]

def _skip_static_section(fp):
    """Skip static section (header + one data record)."""
    meta = _read_section_header(fp)
    _ = _read_values(fp, meta["total_values"])

def read_fort10_dynamic(path):
    """
    Read dynamic section of fort.10.
    Returns dict: key -> np.ndarray
      - Scalars vs time: shape (Nt,)
      - Arrays vs time:  shape (Nt, N)
    """
    with open(path, "r") as fp:
        # 1) Skip static section
        _skip_static_section(fp)
        # 2) Dynamic header
        dyn_meta = _read_section_header(fp)
        items = dyn_meta["items"]
        rec_n = dyn_meta["total_values"]

        # Prepare containers
        data = {name: [] for name, _ in items}

        # 3) Read frames until EOF
        while True:
            pos = fp.tell()
            test = fp.readline()
            if not test:
                break
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

    # Convert lists to arrays
    out = {}
    for k, seq in data.items():
        a = np.array(seq, dtype=float)
        out[k] = a if a.ndim > 1 else a.astype(float)
    return out

# -----------------------------
# Plotting logic
# -----------------------------

def main():
    ap = argparse.ArgumentParser(description="Plot density profile ρ(x) at one time from MULTI fort.10 (PDF).")
    ap.add_argument("-f", "--file", default="fort.10", help="Path to fort.10")
    ap.add_argument("--time_ps", type=float, help="Target time in picoseconds (nearest frame used)")
    ap.add_argument("--frame", type=int, help="Exact frame index (0-based)")
    ap.add_argument("-o", "--out", default="density_profile.pdf", help="Output filename (use .pdf for vector)")
    ap.add_argument("--smooth", type=int, default=1, help="Optional boxcar smoothing over k cells")
    ap.add_argument("--title", default=None, help="Custom plot title")
    args = ap.parse_args()

    dyn = read_fort10_dynamic(args.file)

    # Need TIME (s), R (g/cc at cell centers), XC (cm at cell centers)
    for k in ("TIME", "R", "XC"):
        if k not in dyn:
            raise SystemExit(f"fort.10 missing required variable '{k}'")

    t  = np.asarray(dyn["TIME"])      # shape (Nt,)
    R  = np.asarray(dyn["R"])         # shape (Nt, N)
    XC = np.asarray(dyn["XC"])        # shape (Nt, N)

    if R.ndim != 2 or XC.ndim != 2:
        raise SystemExit("Unexpected shapes: expecting R (Nt,N) and XC (Nt,N).")

    Nt, N = R.shape

    # Choose frame
    if args.frame is not None:
        idx = int(np.clip(args.frame, 0, Nt - 1))
    elif args.time_ps is not None:
        target_s = args.time_ps * 1e-12
        idx = int(np.abs(t - target_s).argmin())
    else:
        idx = Nt - 1  # default: last frame

    x_um = XC[idx] * 1e4      # cm -> μm
    rho  = R[idx].copy()      # g/cc

    # Optional smoothing (simple boxcar)
    if args.smooth and args.smooth > 1:
        k = int(args.smooth)
        kernel = np.ones(k, dtype=float) / k
        rho = np.convolve(rho, kernel, mode="same")

    # Plot
    plt.figure()
    plt.plot(x_um, rho, lw=1.8)
    plt.xlabel("distance [μm]")
    plt.ylabel("density [g/cc]")
    t_ps = t[idx] * 1e12
    plt.title(args.title or f"ρ(x) at t ≈ {t_ps:.3g} ps")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out)  # .pdf gives vector output
    print(f"Wrote {args.out}  (frame {idx}/{Nt-1}, time ≈ {t_ps:.3g} ps)")

if __name__ == "__main__":
    main()

