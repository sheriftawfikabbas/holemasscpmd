"""Production-code (patched QE 6.7.0 cp.x) check of the occupation rule: extract, summarize, plot.

Four NVE restarts from the same damped ground state, 20 000 steps each (../../qe_product_test):

    case                  f_u    mu_o  mu_u  mu_h   mu_o/mu_u   1/f_u   predicted
    fu0.50_mo400_mu200    0.50   400   200   1000   2           2       marginal
    fu0.50_mo600_mu200    0.50   600   200   1000   3           2       heats
    fu0.25_mo600_mu200    0.25   600   200    600   3           4       stable
    fu0.25_mo1000_mu200   0.25  1000   200    600   5           4       heats

  python3 code/qecp_product_analyze.py extract [source_dir]     # sys.evp -> code/qecp_product_runs/*.csv
  python3 code/qecp_product_analyze.py plot                   # CSVs -> figures/qe_product_test.{png,pdf}, summary CSV

cp.x appends to sys.evp, and a relaunched run restarts the step counter at the restart value, so a file can
hold several blocks; ``extract`` keeps the last block only (the one whose first step is the restart step).
"""
import csv
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "qecp-matplotlib"))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = HERE / "qecp_product_runs"
DEFAULT_SOURCE = ROOT   # directory holding the finished case directories
COLUMNS = ("nfi", "time_ps", "ekinc", "T_cell", "T_ion", "etot", "enthalpy", "econs", "econt")
CASES = {  # name: (f_u, mu_o, mu_u, mu_h)
    "fu0.50_mo400_mu200": (0.50, 400, 200, 1000),
    "fu0.50_mo600_mu200": (0.50, 600, 200, 1000),
    "fu0.25_mo600_mu200": (0.25, 600, 200, 600),
    "fu0.25_mo1000_mu200": (0.25, 1000, 200, 600),
}
STYLE = {"fu0.50_mo400_mu200": ("#0072B2", "-"), "fu0.50_mo600_mu200": ("#0072B2", "--"),
         "fu0.25_mo600_mu200": ("#D55E00", "-"), "fu0.25_mo1000_mu200": ("#D55E00", "--")}


def read_evp(path):
    rows = [l.split() for l in Path(path).read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    a = np.array([r[:len(COLUMNS)] for r in rows], float)
    resets = [i for i in range(1, len(a)) if a[i, 0] <= a[i - 1, 0]]
    return a[resets[-1]:] if resets else a


def extract(source):
    RUNS.mkdir(exist_ok=True)
    for name in CASES:
        a = read_evp(Path(source) / name / "sys.evp")
        with open(RUNS / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(a.tolist())
        print(f"{name}: {len(a)} steps, nfi {int(a[0, 0])}..{int(a[-1, 0])}")


def load():
    out = {}
    for name in CASES:
        a = np.genfromtxt(RUNS / f"{name}.csv", delimiter=",", names=True)
        out[name] = {c: a[c] for c in COLUMNS}
    return out


def summarize(data, window=1000):
    rows = []
    for name, d in data.items():
        fu, mo, mu, mh = CASES[name]
        n = len(d["nfi"]) - 1                      # steps since restart
        last = slice(-window, None)
        row = dict(case=name, f_u=fu, mu_o=mo, mu_u=mu, mu_h=mh, ratio=mo / mu, threshold=1 / fu,
                   x=mo / mu * fu, steps=n,
                   econs_start=d["econs"][0], econs_last=float(d["econs"][last].mean()),
                   econt_change=float(d["econt"][last].mean() - d["econt"][0]),
                   ekinc_last=float(d["ekinc"][last].mean()), ekinc_max=float(d["ekinc"].max()),
                   T_ion_last=float(d["T_ion"][last].mean()))
        row["econs_change"] = row["econs_last"] - row["econs_start"]
        half = d["nfi"] >= d["nfi"][0] + n // 2
        row["econs_slope_per_1k"] = float(np.polyfit(d["nfi"][half], d["econs"][half], 1)[0] * 1000)
        row["ekinc_slope_per_1k"] = float(np.polyfit(d["nfi"][half], d["ekinc"][half], 1)[0] * 1000)
        rows.append(row)
    return rows


def plot(data, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
    labels = {n: rf"$f_u={fu:g}$, $\mu_o/\mu_u={mo / mu:g}$ ($1/f_u={1 / fu:g}$)" for n, (fu, mo, mu, mh) in CASES.items()}
    for name, d in data.items():
        color, ls = STYLE[name]
        t = d["time_ps"] - d["time_ps"][0]
        w = 50
        k = np.ones(w) / w
        for ax, key, shift in ((axes[0], "ekinc", False), (axes[1], "econs", True), (axes[2], "econt", True)):
            y = d[key] - (d[key][0] if shift else 0.0)
            y = np.convolve(y, k, mode="valid")
            ax.plot(t[w - 1:], y, color=color, ls=ls, lw=1.3, label=labels[name])
    axes[0].set(yscale="log", ylabel=r"fictitious kinetic energy $E_{\rm kinc}$ (Ha)")
    axes[1].set_yscale("symlog", linthresh=0.1)
    axes[1].set_ylabel(r"$E_{\rm cons}(t)-E_{\rm cons}(0)$ (Ha)")
    axes[2].set_yscale("symlog", linthresh=0.1)
    axes[2].set_ylabel(r"$E_{\rm cons}+E_{\rm kinc}$ change (Ha)")
    for ax, tag in zip(axes, "abc"):
        ax.set_title(f"({tag})", fontsize=9, loc="left")
    for ax in axes:
        ax.set_xlabel("time since restart (ps)")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(0.0, 0.93))
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"qe_product_test.{suffix}", dpi=180)
    plt.close(fig)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plot"
    if cmd == "extract":
        extract(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SOURCE)
    elif cmd == "plot":
        data = load()
        rows = summarize(data)
        with open(RUNS / "summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        plot(data, ROOT / "figures")
        for r in rows:
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
