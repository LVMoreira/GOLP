#!/bin/bash
#SBATCH --job-name=Multi_fs_job
#SBATCH --account=f202508150cpcaa3a
#SBATCH --partition=dev-arm
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G

module purge
module load GCC/12

cd "$SLURM_SUBMIT_DIR"
# If your run needs MULTI libs, add them. If not, you can omit this line.
export LD_LIBRARY_PATH=/projects/F202508150CPCAA3/Lucas/MULTI_FS/lib-4.1:$LD_LIBRARY_PATH

# Run the ARM build; MULTI reads block & fort.12 from CWD
srun /projects/F202508150CPCAA3/Lucas/MULTI_FS/bin/multi-ife-arm |& tee run.log
