# Production-code check of the occupation-proportional mass rule

Four 20 000-step NVE restarts of a C4H6 molecule (10 atoms, 15 Å cell, `ecutwfc` 60 Ry,
`nspin = 2`, `dt = 3`, no thermostat) with the patched Quantum ESPRESSO 6.7.0 `cp.x`
of this repository. They test whether the heating threshold follows
`mu_o/mu_u = f_o/f_u = 1/f_u`.

| case | f_u | mu_o | mu_u | mu_h | mu_o/mu_u | 1/f_u | result after 20 000 steps |
|---|---|---|---|---|---|---|---|
| `fu0.50_mo400_mu200` | 0.50 | 400 | 200 | 1000 | 2 | 2 | quiet (E_kinc 0.015 Ha) |
| `fu0.50_mo600_mu200` | 0.50 | 600 | 200 | 1000 | 3 | 2 | runs away (E_kinc 6.7 Ha, E_cons +2.5 Ha) |
| `fu0.25_mo600_mu200` | 0.25 | 600 | 200 | 600 | 3 | 4 | no runaway (E_cons slope -0.002 Ha / 1000 steps) |
| `fu0.25_mo1000_mu200` | 0.25 | 1000 | 200 | 600 | 5 | 4 | runs away (E_kinc 12.8 Ha, E_cons +7.7 Ha) |

One trajectory per case. The result is consistent with the occupation rule and
inconsistent with a fixed 2:1 ratio; it does not locate the threshold and does not attribute
the heating to the constraint. The f_u = 0.25 runs begin with a sudden switch of the
occupations from (0.5, 0.5) to (0.75, 0.25).

## Contents

| path | what |
|---|---|
| `inputs/*.scf.in` | the four `cp.x` inputs as run |
| `make_cases.py` | builds the case directories from a base `scf.in` (regex-substitutes `nstep`, `emass`, `emptymass`, `hmass` and the occupation row) |
| `run_tmux.sh` | starts the four cases detached in one tmux session (9 MPI ranks each) |
| `run_all.sh` | same, with `nohup` instead of tmux |
| `code/qecp_product_analyze.py` | `extract` (case `sys.evp` -> CSV) and `plot` (CSV -> figure and `summary.csv`) |
| `code/qecp_product_runs/*.csv` | extracted time series (`nfi, time_ps, ekinc, T_cell, T_ion, etot, enthalpy, econs, econt`) and `summary.csv` |
| `figures/qe_product_test.{png,pdf}` | E_kinc, E_cons and E_cons + E_kinc against time |

## Reproducing

Needed but not included: the damped ground-state restart `GS/sys_50.save`, its two
pseudopotentials (`C.pbe-n-rrkjus_psl.1.0.0.UPF`, `H.pbe-rrkjus_psl.1.0.0.UPF`) and the base
`scf.in` of the original run (`Rescaling_5000_NoThermostat/scf.in`: `dt = 3`, `electron_damping = 0.1`,
Verlet ions with no thermostat). `make_cases.py` expects them under `../0.5_600_1000_200/`
(edit `SRC`). The GS was a damped electronic minimization at fixed ions with occupations
(0.5, 0.5) for the hole and excited bands.

```bash
python3 make_cases.py                                  # writes the four case directories
CPX=/path/to/patched/cp.x C=$CONDA_PREFIX ./run_tmux.sh   # ~7 steps/min per case on a loaded 36-core node
python3 code/qecp_product_analyze.py extract           # after the runs finish
python3 code/qecp_product_analyze.py plot
```

A relaunched run appends to `sys.evp` and restarts its step counter at the restart value
(3406 here), so a file may hold several blocks; `extract` keeps only the last.

## Building the patched `cp.x` (notes from this build)

* The tarball's paths begin with `q-e-qe-6.7.0/`, so from the directory containing the
  source tree apply it with `patch -p1` (the `-p0` form in the top-level README did not
  apply here).
* With a conda OpenMPI toolchain: `OMPI_FC=gfortran OMPI_CC=gcc`, `./configure`, and set
  `BLAS_LIBS` in `make.inc` to the available BLAS (`-lblas` for the conda env; `-lopenblas`
  was not found), then `make cp`.
* The patch's constraint is mass-blind (common `dt^2/emass` factor), and `ekinc` uses `emass`.
