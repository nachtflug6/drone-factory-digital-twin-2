# Getting Started with the WS Conveyor Digital Twin Project

Welcome! This guide will help you set up your environment and understand the project scope.

---

## Important: About the Documentation Translation

### What You're Working With

The **Kod_WSConv_Sven2022.pdf** documentation contains the PLC (Programmable Logic Controller) code for the WS Conveyor system. Your task is to **translate this documentation into executable Python code** that faithfully reproduces the system behavior.

### Key Points

✅ **Reference Implementation Provided**  
We've created a **backbone/skeleton** in this repository:
- [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) — Initial system analysis  
- [src/mock_up/components.py](src/mock_up/components.py) — 7 component classes with basic structure
- [src/mock_up/config.py](src/mock_up/config.py) — Parameters extracted from documentation

⚠️ **This is NOT Complete**  
What's provided is **orientation and starting point**, not a finished implementation. Students must:
- Extend the component classes with more detail
- Implement the actual control logic from the PLC code
- Add missing components and states
- Verify against the documentation

📄 **Translation Doesn't Need to Be 1:1**  
You can **simplify** the PLC code while preserving core behavior:
- Focus on key control logic, not every single variable
- Merge similar patterns
- Ignore hardware-specific details (I/O addresses, etc.)
- Prioritize functional correctness over exact replication

🤖 **LLM-Assisted Translation Possible**  
You can use AI tools (like this one) to help:
- Parse PLC code structure
- Identify state machines
- Suggest Python translations
- Generate test cases

⚠️ **Visual Logic Requires Manual Analysis**  
Some PLC code is **graphical** (ladder logic, SFC diagrams):
- Shows logical connections between variables
- Represents conditions, transitions, sequences
- Needs to be understood visually and translated conceptually
- See pages 12-15, 21-30 in Kod_WSConv_Sven2022.pdf for examples

---

## Setup Options

Choose the setup method that works best for your environment:

### Option 1: Local Development (Recommended for Starting)

**Best for**: Individual learning, quick iteration, debugging

```bash
# 1. Clone/download repository
cd drone-factory-digital-twin

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python examples/ws_conveyor_simulation.py
```

**Expected output**:
```
================================================================================
  WS CONVEYOR SYSTEM SIMULATION
================================================================================
Duration: 24.0 hours
Timestep: 0.1 seconds
...
✅ All system-specific components loaded successfully!
```

---

### Option 2: Docker Container (Reproducible Environment)

**Best for**: Ensuring consistent environment across team, deployment

#### Prerequisites
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))

#### Setup

**Create Dockerfile** (in project root):
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command
CMD ["python", "examples/ws_conveyor_simulation.py"]
```

**Build and run**:
```bash
# Build image
docker build -t ws-conveyor-twin .

# Run simulation
docker run ws-conveyor-twin

# Run with shell access
docker run -it ws-conveyor-twin bash

# Run with volume mount (for development)
docker run -it -v $(pwd):/app ws-conveyor-twin bash
```

**For Jupyter notebooks** (analysis phase):
```bash
docker run -p 8888:8888 ws-conveyor-twin \
    jupyter notebook --ip=0.0.0.0 --allow-root
```

---

### Option 3: Apptainer/Singularity (HPC Cluster Deployment)

**Best for**: Running simulations on university/research clusters, long-horizon runs

#### Prerequisites
- Apptainer/Singularity installed on cluster
- Access to HPC resources

#### Create Apptainer Definition File

**ws_conveyor.def**:
```singularity
Bootstrap: docker
From: python:3.11-slim

%files
    requirements.txt /app/requirements.txt
    src /app/src
    examples /app/examples
    docs /app/docs

%post
    # Update and install dependencies
    apt-get update
    apt-get install -y build-essential git
    
    # Install Python packages
    cd /app
    pip install --no-cache-dir -r requirements.txt
    
    # Cleanup
    apt-get clean
    rm -rf /var/lib/apt/lists/*

%environment
    export PYTHONPATH=/app:$PYTHONPATH

%runscript
    cd /app
    python examples/ws_conveyor_simulation.py "$@"

%labels
    Author Students
    Version 1.0
    Description WS Conveyor Digital Twin Simulation
```

#### Build and Deploy

**On your local machine** (with sudo):
```bash
# Build container image
sudo apptainer build ws_conveyor.sif ws_conveyor.def
```

**On HPC cluster** (no sudo needed):
```bash
# Transfer .sif file to cluster
scp ws_conveyor.sif username@cluster:/path/to/project/

# Run simulation
apptainer run ws_conveyor.sif

# Run with custom script
apptainer exec ws_conveyor.sif python my_simulation.py

# Run long-horizon simulation as batch job
sbatch run_simulation.sh
```

**Example SLURM batch script** (`run_simulation.sh`):
```bash
#!/bin/bash
#SBATCH --job-name=ws_conveyor_sim
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=simulation_%j.log

module load apptainer

# Run 7-day simulation
apptainer exec ws_conveyor.sif python -c "
from src.mock_up.config import config_long_horizon
from examples.ws_conveyor_simulation import simulate_ws_conveyor

config = config_long_horizon()
simulate_ws_conveyor()
"

echo "Simulation complete. Check data/logs/ for output."
```

---

## Verification: Did Setup Work?

### Test 1: Basic Import
```bash
python3 -c "
from src.mock_up.config import config_normal_operation
from src.mock_up.components import create_ws_conveyor_system

config = config_normal_operation()
components = create_ws_conveyor_system(config)
print(f'✅ Success! Created {len(components)} components')
"
```

### Test 2: Run Example
```bash
python examples/ws_conveyor_simulation.py
```

Should see:
```
✓ Conveyor motor: main_conveyor
✓ Elevator: transfer_elevator
✓ Buffer: buffer
✓ Pneumatic: pneumatic_system
✓ RFID readers: rfid_queue, rfid_elevator
✓ Stations: DS1-DS6

✅ All system-specific components loaded successfully!
```

---

## Understanding the Project Structure

### Your Mission

**Translate Kod_WSConv_Sven2022.pdf → Executable Python Code**

The PLC documentation shows:
- Component specifications (motors, conveyors, elevators, sensors)
- State machines (IDLE → RUNNING → STOPPED, etc.)
- Control logic (when to start/stop, how to sequence operations)
- Timing constraints (ramp times, delays, detection windows)
- Safety interlocks (pressure limits, buffer overflow prevention)

You need to:
1. **Understand** the system by analyzing the PDF
2. **Translate** PLC logic into Python components
3. **Verify** your code matches documented behavior
4. **Simulate** long-horizon runs (24+ hours)
5. **Analyze** system dynamics and patterns

### What's Already Done (Reference/Backbone)

✅ **System Analysis** — [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md)
- Analyzed major components from PDF
- Extracted key parameters
- Documented state machines
- **Status**: Starting point, needs more detail

✅ **Component Classes** — [src/mock_up/components.py](src/mock_up/components.py)
- 7 component classes with basic structure
- State enums defined
- Core methods (start, stop, update)
- **Status**: Skeleton only, needs implementation

✅ **Configuration** — [src/mock_up/config.py](src/mock_up/config.py)
- Parameters extracted from documentation
- Timing values, physical limits
- **Status**: Good starting values, may need tuning

❌ **Control Logic** — [src/mock_up/logic.py](src/mock_up/logic.py)
- Template structure only
- **Students must implement**

❌ **Simulator** — [src/simulation/](src/simulation/)
- Empty framework
- **Students must implement**

❌ **Tests** — [tests/](tests/)
- Example pattern provided
- **Students must write comprehensive tests**

### What Students Must Do

1. **Phase 1 (Weeks 1-2): Enhanced System Analysis**
   - Study Kod_WSConv_Sven2022.pdf in detail
   - Extend [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md)
   - Document ALL states, transitions, signals
   - Identify visual logic in SFC diagrams (pages 12-15)
   - Create detailed component specifications

2. **Phase 2 (Weeks 3-5): Implementation**
   - Extend component classes with actual PLC logic
   - Implement [src/mock_up/logic.py](src/mock_up/logic.py) control rules
   - Translate state machines from documentation
   - Handle edge cases and error conditions

3. **Phase 3 (Weeks 6-7): Verification**
   - Write unit tests for each component
   - Write integration tests for sequences
   - Verify against documentation
   - Achieve >80% code coverage

4. **Phase 4 (Weeks 8-9): Simulation**
   - Build event-driven simulator
   - Implement comprehensive logging
   - Run 24+ hour simulations
   - Collect system behavior data

5. **Phase 5 (Weeks 10-13): Analysis**
   - Parse logs and extract patterns
   - Visualize state timelines
   - Analyze throughput, reliability
   - Document findings

---

## Quick Reference: Key Files

| What You Need | File | Status |
|---------------|------|--------|
| **System Documentation** | [Kod_WSConv_Sven2022.pdf](docs/Kod_WSConv_Sven2022.pdf) | ✅ Source |
| **System Analysis** | [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) | 🟡 Backbone |
| **Components** | [src/mock_up/components.py](src/mock_up/components.py) | 🟡 Skeleton |
| **Configuration** | [src/mock_up/config.py](src/mock_up/config.py) | ✅ Reference |
| **Logic** | [src/mock_up/logic.py](src/mock_up/logic.py) | ❌ To implement |
| **Example** | [examples/ws_conveyor_simulation.py](examples/ws_conveyor_simulation.py) | ✅ Working |
| **Project Phases** | [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) | ✅ Timeline |
| **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | ✅ Patterns |
| **PLC Translation Guide** | [docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md) | ✅ How-to |

---

## Tips for Success

### Understanding PLC Code

The **Kod_WSConv_Sven2022.pdf** contains different types of PLC code:

1. **Structured Text (ST)** — Text-based code, easier to parse
   - Can be translated almost line-by-line
   - Look for: IF/THEN, CASE, WHILE loops

2. **Sequential Function Chart (SFC)** — Visual state machine (pages 12-15, 28-30)
   - Shows steps and transitions
   - Translate to Python state enums + transition functions
   - Example: INIT → RECEIVING → PROCESSING → SENDING

3. **Function Blocks (FB)** — Reusable logic blocks
   - Translate to Python classes
   - Example: `FB_MC_DOS_Control_DS2toDS6_V1` → `DockingStation` class

4. **Global Variable Lists (GVL)** — Configuration data (pages 33-39)
   - Extract to [src/mock_up/config.py](src/mock_up/config.py)
   - Example: `hmi_conveyer_speed`, `ifm_q3_pressure_sensor_value`

### Translation Strategy

**Don't try to translate everything at once!**

1. Start with ONE component (e.g., conveyor motor)
2. Identify its states from SFC diagrams
3. List inputs and outputs
4. Implement basic state machine
5. Test thoroughly
6. Move to next component

**Prioritize**:
- ✅ Core functionality (start, stop, state transitions)
- ✅ Timing constraints (ramps, delays)
- ✅ Safety interlocks (limits, overflows)
- 🟡 Detailed error handling (implement later)
- ❌ Hardware specifics (ignore EtherCAT addresses, etc.)

### Using LLMs for Translation

You can use AI assistants (like this one) to:
- Parse PLC code sections
- Generate Python class structures
- Suggest state machine implementations
- Create test cases

**Example prompt**:
```
Here's a section of PLC code from Kod_WSConv_Sven2022.pdf:

[paste code section]

Please help me translate this to Python:
1. Identify the state machine
2. List inputs and outputs
3. Suggest a Python class structure
4. Generate example test cases
```

**But remember**: LLMs can help, but YOU must:
- Verify the logic is correct
- Understand what the code does
- Test thoroughly
- Take responsibility for correctness

---

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the project root
cd drone-factory-digital-twin

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Docker Build Fails
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker build --no-cache -t ws-conveyor-twin .
```

### Apptainer on Cluster
```bash
# Check Apptainer is available
module avail apptainer
module load apptainer

# Test locally first
apptainer shell ws_conveyor.sif
```

---

## Next Steps

1. **Verify Setup** — Run the tests above ✅
2. **Read Project Overview** — [README.md](README.md) (10 min)
3. **Understand Phases** — [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) (15 min)
4. **Study System Analysis** — [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) (30 min)
5. **Read PDF Documentation** — [Kod_WSConv_Sven2022.pdf](docs/Kod_WSConv_Sven2022.pdf) (2-3 hours)
6. **Begin Phase 1** — Start analyzing and documenting the system

---

## Getting Help

**Documentation Issues?**
- Check [INDEX.md](INDEX.md) for navigation
- Read [docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md) for translation guidance

**Code Issues?**
- Review [src/mock_up/components.py](src/mock_up/components.py) for examples
- Check [tests/unit/test_motor.py](tests/unit/test_motor.py) for test patterns

**Conceptual Questions?**
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design patterns
- Review [docs/SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md) for simulation concepts

**Progress Tracking?**
- Use [STUDENT_CHECKLIST.md](STUDENT_CHECKLIST.md) to track your work

---

**Good luck! 🚀**

Remember: The goal is not to create a perfect 1:1 translation, but to build a functional digital twin that captures the essential behavior of the WS Conveyor system for analysis and simulation.
