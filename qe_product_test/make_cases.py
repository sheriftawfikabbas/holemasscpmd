"""Generate the QE (patched cp.x 6.7.0) test of the occupation-proportional rule.

Base: ../0.5_600_1000_200/Rescaling_5000_NoThermostat/scf.in (the diverged NVE run) restarted
from the damped ground state ../0.5_600_1000_200/GS/sys_50.save (occupations 0.5/0.5).
Each case changes only the occupations of the hole/excited pair and (emass, emptymass); hmass
stays 1000 as in the original run; dt = 3, NVE, ion velocities zero (restart from GS).

Model prediction (mass-blind constraint): heating iff mu_o/mu_u > f_o/f_u = 1/f_u.
  fu=0.50: threshold 2   -> ratio 3 heats (the original run), ratio 2 marginal (published: fine)
  fu=0.25: threshold 4   -> ratio 3 should NOT heat, ratio 5 should.
"""
import re, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "0.5_600_1000_200"
# name, f_u, emass (mu_o), emptymass (mu_u), hmass (mu_h)
# At fu=0.25 mu_h = mu_u f_h/f_u = 600 keeps the hole-excited pair marginal; hmass=1000 would add
# an artificial anti-restoring hole-excited direction (f_h/mu_h < f_u/mu_u) and confound the test.
CASES = [
    ("fu0.50_mo600_mu200", 0.50, 600, 200, 1000),   # reproduces the diverged run (ratio 3 > 2)
    ("fu0.50_mo400_mu200", 0.50, 400, 200, 1000),   # control, ratio 2
    ("fu0.25_mo600_mu200", 0.25, 600, 200, 600),    # ratio 3 < 4: predicted stable (discriminating)
    ("fu0.25_mo1000_mu200", 0.25, 1000, 200, 600),  # ratio 5 > 4: predicted heating
]
NSTEP = 20000

base = (SRC / "Rescaling_5000_NoThermostat" / "scf.in").read_text()
for name, fu, mo, mu, mh in CASES:
    d = HERE / name
    d.mkdir(exist_ok=True)
    for f in ("C.pbe-n-rrkjus_psl.1.0.0.UPF", "H.pbe-rrkjus_psl.1.0.0.UPF"):
        shutil.copy(SRC / "GS" / f, d / f)
    if not (d / "sys_50.save").exists():
        shutil.copytree(SRC / "GS" / "sys_50.save", d / "sys_50.save")
    t = base
    t = re.sub(r"nstep = \d+", f"nstep = {NSTEP}", t)
    t = re.sub(r"emass =\s+\d+", f"emass = {mo}", t)
    t = re.sub(r"emptymass = \d+", f"emptymass = {mu}", t)
    t = re.sub(r"hmass = \d+", f"hmass = {mh}", t)
    fh = 1.0 - fu
    row = lambda last: "1 1 1 1 1 1 1 1 1 1 %g %g 0 0" % (fh, fu)
    t = t.replace("1 1 1 1 1 1 1 1 1 1 0.5 0.5 0 0", row(0))
    (d / "scf.in").write_text(t)
    print(name, "f=(%g,%g)" % (fh, fu), "mu=(%d,%d,%d)" % (mo, mh, mu), "ratio", mo / mu, "threshold", 1 / fu)
