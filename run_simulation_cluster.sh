#!/bin/bash
#SBATCH --job-name=ws_conveyor_sim
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=simulation_%j.log
#SBATCH --error=simulation_%j.err

# WS Conveyor Digital Twin - Long Horizon Simulation
# SLURM batch script for HPC cluster deployment

echo "=========================================="
echo "WS Conveyor Simulation - Job $SLURM_JOB_ID"
echo "=========================================="
echo "Started: $(date)"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE MB"
echo ""

# Load required modules (adjust for your cluster)
module load apptainer

# Set simulation parameters
DURATION_HOURS=168  # 7 days
TIMESTEP=1.0        # 1 second timestep
OUTPUT_DIR="data/logs/job_${SLURM_JOB_ID}"

# Create output directory
mkdir -p $OUTPUT_DIR

echo "Configuration:"
echo "  Duration: $DURATION_HOURS hours"
echo "  Timestep: $TIMESTEP seconds"
echo "  Output: $OUTPUT_DIR"
echo ""

# Run simulation
echo "Starting simulation..."
apptainer exec ws_conveyor.sif python -c "
import sys
sys.path.insert(0, '.')

from src.mock_up.config import SimulationConfig
from src.mock_up.components import create_ws_conveyor_system

# Configure long-horizon simulation
config = SimulationConfig(
    duration_hours=${DURATION_HOURS},
    timestep_seconds=${TIMESTEP},
    log_file='${OUTPUT_DIR}/simulation.jsonl',
    log_level='INFO',
    log_state_snapshots=True,
    snapshot_interval_seconds=300.0,
    seed=42
)

print('Configuration loaded')
print(f'Duration: {config.duration_hours} hours')
print(f'Timestep: {config.timestep_seconds} seconds')
print(f'Output: {config.log_file}')

# Create system
components = create_ws_conveyor_system(config)
print(f'System created: {len(components)} components')

# Run simulation (students will implement the actual simulator)
print('Simulation would run here...')
print('Note: Full simulator implementation is part of Phase 4')
print('This script demonstrates cluster deployment setup')

print('✓ Job completed successfully')
"

echo ""
echo "Simulation completed: $(date)"
echo "Output saved to: $OUTPUT_DIR"
echo ""
echo "To analyze results:"
echo "  apptainer exec ws_conveyor.sif python analysis/scripts/analyze_logs.py $OUTPUT_DIR"

# Optional: Copy results to persistent storage
# cp -r $OUTPUT_DIR /path/to/persistent/storage/

exit 0
