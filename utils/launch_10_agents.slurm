#!/bin/bash

#SBATCH --job-name=cluster-sentinel-clients
#SBATCH --array=1-10                     # Create 10 array jobs (clients)
#SBATCH --nodes=1                        # Each task needs 1 node (can be shared)
#SBATCH --ntasks=1                       # Run 1 task per array job
#SBATCH --cpus-per-task=1                # Ask for 1 CPU per task
#SBATCH --time=00:10:00                  # Job runtime limit
#SBATCH --output=logs/agent_client_%A_%a.log   # Log file for each client

echo "Starting Agent Client $SLURM_ARRAY_TASK_ID on $(hostname)..."

# Run the agent connecting to the specified host and port
python -u agent.py --host 192.168.0.1 --port 13580
