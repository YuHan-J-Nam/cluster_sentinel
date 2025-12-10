#!/bin/bash

#SBATCH --job-name=agent_cluster
#SBATCH --output=agent_cluster_%j.out
#SBATCH --error=agent_cluster_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=10                 # Request 10 tasks (agents)
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00             # 1 hour runtime
#SBATCH --mem-per-cpu=100M          # 100MB per CPU

# Load any necessary modules (e.g., Python)
# module load python/3.x  # Uncomment and adjust if needed on your HPC

# Master server details
MASTER_HOST="localhost"   # Assuming master is running on the login node or via tunnel
MASTER_PORT=13579

echo "Launching 10 agents..."

for i in $(seq 0 9); do
    echo "Starting agent $i..."
    python ../agent.py --host $MASTER_HOST --port $MASTER_PORT &
    sleep 1 # Stagger agent start times slightly
done

echo "All agents launched. Waiting for them to finish (or for job to be scancelled)..."
wait # Wait for all background processes to complete
echo "All agents terminated."
