#!/bin/bash

#SBATCH --job-name=monitor-agent         # Name of the job
#SBATCH --nodes=1                        # Run on a single node
#SBATCH --ntasks=1                       # Run a single task
#SBATCH --cpus-per-task=1                # Ask for 1 CPU
#SBATCH --time=00:05:00                  # Job runtime (5 minutes)
#SBATCH --output=logs/agent_%j.log            # Log file for agent output
# SBATCH --output=agent_array_%A_%a.log   # %A is array ID, %a is task ID
# SBATCH --array=1-5                      # Create 5 array jobs

echo "Starting Agent on Compute Node..."
echo "Target Master IP: 163.180.2.245 (Login Node Public IP)"

# Run the agent (unbuffered mode)
python -u agent.py --host 163.180.2.245 --port 13580
