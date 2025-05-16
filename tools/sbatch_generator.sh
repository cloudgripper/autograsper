#!/bin/bash

PTH_DIR="/workspaces/CloudGripper_Stack_1k/assets/pre_trained_weights/visual_features/resnet18"
BASE_DIR="/home/x_shuji/CloudGripper_Stack_1k/sbatch"
PARENT_DIR="$(dirname "$BASE_DIR")" 
DATA_DIR="/workspaces/CloudGripper_Stack_1k/assets/dataset/CloudGripper_stack_1k/limited_init_positions"
FEATURE="agent=resnet" 

EXP_NAME=$(basename "$PTH_DIR")

for PTH_FILE in ${PTH_DIR}/*.pth; do
  PTH_BASENAME=$(basename -- "$PTH_FILE")
  PTH_NAME="${PTH_BASENAME%.*}"

  SBATCH_FILE="${BASE_DIR}/${EXP_NAME}_${PTH_NAME}.sh"

  cat <<EOF >"$SBATCH_FILE"
#!/bin/bash
#SBATCH --gpus 8
#SBATCH -t 12:00:00
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user shutong@kth.se
#SBATCH -o ${PARENT_DIR}/logs/slurm-%A.out
#SBATCH -e ${PARENT_DIR}/logs/slurm-%A.err

module load Anaconda/2021.05-nsc1
cd ${PARENT_DIR}
conda activate data4robotics

python finetune.py exp_name=${EXP_NAME} \\
       agent.features.restore_path=${PTH_FILE} \\
       buffer_path=${DATA_DIR}/limited_init_positions.pkl\\
       devices=8 \\
       ${FEATURE} \\
       wandb.name=${EXP_NAME}_${PTH_NAME}
EOF

  # Make the SBATCH script executable
  chmod +x "$SBATCH_FILE"
done
