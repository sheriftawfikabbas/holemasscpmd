#!/bin/bash
# Start the four QE cases detached in one tmux session (survives closing terminals / logging out).
#   ./run_tmux.sh            start        tmux attach -t qe_test     look      Ctrl-b d   detach
set -e
cd "$(dirname "$0")"; ROOT=$PWD
S=${SESSION:-qe_test}
C=${C:-$CONDA_PREFIX}          # environment providing mpirun (OpenMPI) and its libraries
CPX=${CPX:?set CPX to the patched QE 6.7.0 cp.x}
NP=${NP:-9}
tmux has-session -t "$S" 2>/dev/null && { echo "tmux session $S already exists"; exit 1; }
for d in fu*/; do
  if [ -n "$(find /proc -maxdepth 2 -name cwd -lname "$ROOT/${d%/}" 2>/dev/null)" ]; then
    echo "a process is already running in $d; stop it first"; exit 1; fi
done
first=1
for d in fu*/; do d=${d%/}
  cmd="export PATH=$C/bin:\$PATH LD_LIBRARY_PATH=$C/lib OMP_NUM_THREADS=1; cd $ROOT/$d && mpirun -np $NP $CPX < scf.in > scf.out 2>&1; echo \"finished (exit \$?) \$(date)\" >> run.status; exec bash"
  if [ $first = 1 ]; then tmux new-session -d -s "$S" -n "$d" "bash -c '$cmd'"; first=0
  else tmux new-window -t "$S" -n "$d" "bash -c '$cmd'"; fi
done
tmux ls | grep "$S"
