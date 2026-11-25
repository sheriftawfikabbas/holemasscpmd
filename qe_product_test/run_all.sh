#!/bin/bash
# usage: CPX=/path/to/patched/cp.x MPIRUN=/path/to/mpirun ./run_all.sh   (starts all 4 cases at once, 9 MPI ranks each = 36 cores)
set -e
cd "$(dirname "$0")"
: "${CPX:?set CPX to the patched QE 6.7.0 cp.x}"; MPIRUN=${MPIRUN:-mpirun}
export OMP_NUM_THREADS=1
for d in fu*/; do
  ( cd $d && nohup $MPIRUN -np 9 $CPX < scf.in > scf.out 2>&1 & )
done
