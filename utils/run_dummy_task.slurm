#!/bin/bash

#SBATCH --job-name=dummy-task            # Name of the job
#SBATCH --nodes=1                        # Run on a single node
#SBATCH --ntasks=1                       # Run a single task
#SBATCH --cpus-per-task=1                # Ask for 1 CPU
#SBATCH --time=00:10:00                  # Job runtime (5 minutes)

python -u dummy_task.py
