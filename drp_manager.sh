#!/usr/bin/sh

export PATH=<ADD PATHS>
export MKL_NUM_THREADS=16
export NUMEXPR_NUM_THREADS=1
export OMP_NUM_THREADS=1
python <ADD_ROOT_PATH>/drp_manager.py $*

