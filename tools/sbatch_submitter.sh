#!/bin/bash

SBATCH_DIR="/home/x_shuji/CloudGripper_Stack_1k/sbatch"
DELAY_SECONDS=3  # Number of seconds to wait between submissions

for sbatch_script in ${SBATCH_DIR}/*.sh; do
    if [[ -f "$sbatch_script" ]]; then
        echo "Submitting $sbatch_script..."
        sbatch "$sbatch_script"
        echo "Waiting for $DELAY_SECONDS seconds..."
        sleep $DELAY_SECONDS
    else
        echo "No SBATCH scripts found in $SBATCH_DIR"
    fi
done