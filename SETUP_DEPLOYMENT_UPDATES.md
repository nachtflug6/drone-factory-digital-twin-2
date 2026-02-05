# Setup & Deployment Updates

## Summary of Changes

This update adds comprehensive setup options for students and clarifies the documentation translation approach.

---

## 1. Getting Started Guide — UPDATED

**File**: [GETTING_STARTED.md](GETTING_STARTED.md)

### Key Additions

✅ **Documentation Translation Clarification**
- Explains that provided code is **backbone/orientation**, not complete
- States explicitly: **1:1 translation NOT required**, can simplify
- Notes that some PLC code is **visual** (SFC diagrams, ladder logic)
- Suggests **LLM-assisted translation** as option
- Sets realistic expectations for student work

✅ **Three Setup Options Added**
1. **Local Development** — Virtual environment (existing method, enhanced docs)
2. **Docker Container** — Reproducible environment for teams
3. **Apptainer/Singularity** — HPC cluster deployment for long simulations

---

## 2. Container Support — NEW FILES

### Docker Configuration

**File**: [Dockerfile](Dockerfile) ✨ NEW

Features:
- Python 3.11 base image
- All project dependencies installed
- Jupyter notebook support for analysis
- Development tools (ipython, vim)
- Output directories pre-created
- Optimized layer caching

**Usage**:
```bash
# Build
docker build -t ws-conveyor-twin .

# Run simulation
docker run ws-conveyor-twin

# Interactive development
docker run -it -v $(pwd):/app ws-conveyor-twin bash

# Jupyter notebooks
docker run -p 8888:8888 ws-conveyor-twin \
    jupyter notebook --ip=0.0.0.0 --allow-root
```

---

### Apptainer/Singularity Configuration

**File**: [ws_conveyor.def](ws_conveyor.def) ✨ NEW

Features:
- HPC cluster compatible (no root required)
- Multiple app modes: simulation, test, jupyter
- Built-in validation tests
- Comprehensive help documentation
- SLURM-ready

**Usage**:
```bash
# Build (requires sudo on local machine)
sudo apptainer build ws_conveyor.sif ws_conveyor.def

# On cluster (no sudo needed)
apptainer run ws_conveyor.sif

# Run tests
apptainer run --app test ws_conveyor.sif

# Custom script
apptainer exec ws_conveyor.sif python my_analysis.py
```

---

### SLURM Batch Script

**File**: [run_simulation_cluster.sh](run_simulation_cluster.sh) ✨ NEW

Features:
- Configured for 24-hour job (7-day simulation)
- 4 CPUs, 8GB RAM (adjustable)
- Automatic log naming with job ID
- Module loading for Apptainer
- Output directory management

**Usage**:
```bash
# Submit to cluster
sbatch run_simulation_cluster.sh

# Check status
squeue -u $USER

# View logs
tail -f simulation_JOBID.log
```

**Customization**:
```bash
# Edit script for different durations
DURATION_HOURS=168  # 7 days
TIMESTEP=1.0        # 1 second

# Adjust resources
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
```

---

## 3. Translation Guide — NEW DOCUMENTATION

**File**: [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) ✨ NEW

Comprehensive 600+ line guide covering:

### Content Sections

1. **What's Been Done**
   - Clear status of reference implementation
   - What students must still implement
   
2. **Translation Philosophy**
   - Goal: Functional twin, NOT 1:1 copy
   - Prioritization: What to translate vs. what to simplify
   - High/Medium/Low priority elements
   
3. **Understanding PLC Code Types**
   - **Structured Text (ST)**: Text-based, line-by-line translation
   - **Sequential Function Chart (SFC)**: Visual state machines, needs interpretation
   - **Function Blocks (FB)**: Maps to Python classes
   - **Global Variable Lists (GVL)**: Configuration extraction
   - **Ladder Logic**: Logical gate translation (if present)
   
4. **Step-by-Step Workflow**
   - Week-by-week translation process
   - Component-by-component approach
   - Testing strategy
   
5. **Using LLMs**
   - Example prompts for translation
   - What LLMs can/cannot do
   - Limitations and best practices
   
6. **Simplification Guidelines**
   - When simplification is acceptable
   - What must NOT be simplified
   - Documentation requirements
   
7. **Verification Strategy**
   - How to validate translation correctness
   - Comparison against reference
   - Testing checklist

---

## 4. Updated Files

### .gitignore — UPDATED

Added entries for:
- Apptainer images (*.sif, *.img)
- Docker artifacts
- SLURM outputs (simulation_*.log, simulation_*.err)
- Jupyter checkpoints
- Compressed archives

---

## Why These Changes?

### Problem 1: Setup Complexity
**Before**: Only local development documented  
**After**: Three deployment options (local, Docker, HPC cluster)  
**Benefit**: Students can choose environment that fits their needs

### Problem 2: Unclear Scope
**Before**: Unclear if provided code is "the answer"  
**After**: Explicit that code is orientation/backbone, not complete  
**Benefit**: Students understand their work scope

### Problem 3: Translation Expectations
**Before**: No guidance on how to translate PLC → Python  
**After**: Comprehensive guide with examples, priorities, and strategies  
**Benefit**: Students have clear methodology

### Problem 4: Visual Code Understanding
**Before**: No mention of SFC diagrams, ladder logic  
**After**: Explains visual code types and how to translate them  
**Benefit**: Students know to read diagrams, not just text

### Problem 5: LLM Usage
**Before**: No guidance on AI-assisted translation  
**After**: Explains how LLMs can help (and limitations)  
**Benefit**: Students can use tools effectively

---

## Use Cases

### Individual Student (Local Development)
```bash
# Clone repo
git clone <repo-url>
cd drone-factory-digital-twin

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start working
python examples/ws_conveyor_simulation.py
```

### Team Project (Docker)
```bash
# Build once, share container
docker build -t ws-conveyor-twin .
docker push registry.university.edu/ws-conveyor-twin

# Each team member pulls and runs
docker pull registry.university.edu/ws-conveyor-twin
docker run -it -v $(pwd):/app ws-conveyor-twin bash
```

### Long-Horizon Analysis (HPC Cluster)
```bash
# Build container locally
sudo apptainer build ws_conveyor.sif ws_conveyor.def

# Transfer to cluster
scp ws_conveyor.sif username@cluster.university.edu:~/

# Submit 7-day simulation
ssh cluster.university.edu
sbatch run_simulation_cluster.sh

# Results in data/logs/job_XXXXX/
```

---

## Student Workflow

### Phase 1: Setup (Week 1)
1. Choose deployment method (local/Docker/cluster)
2. Follow [GETTING_STARTED.md](GETTING_STARTED.md)
3. Verify with: `python examples/ws_conveyor_simulation.py`

### Phase 2: Translation (Weeks 1-5)
1. Read [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md)
2. Analyze Kod_WSConv_Sven2022.pdf
3. Extend components incrementally
4. Test each component thoroughly

### Phase 3: Implementation (Weeks 5-9)
1. Implement full control logic
2. Build simulator
3. Write comprehensive tests

### Phase 4: Analysis (Weeks 9-13)
1. Run long-horizon simulations (Docker/cluster)
2. Analyze logs
3. Generate visualizations
4. Write final report

---

## Verification

### Test Container Builds

**Docker**:
```bash
docker build -t ws-conveyor-twin . && \
docker run ws-conveyor-twin
```

Expected output:
```
Testing WS Conveyor components...
✓ Config loaded: 24.0h duration
✓ Components created: 12 total
...
✅ All system-specific components loaded successfully!
```

**Apptainer** (if sudo available):
```bash
sudo apptainer build ws_conveyor.sif ws_conveyor.def && \
apptainer run ws_conveyor.sif
```

---

## Documentation Structure

```
drone-factory-digital-twin/
├── GETTING_STARTED.md           ← UPDATED: Docker/Apptainer setup
├── Dockerfile                    ← NEW: Container definition
├── ws_conveyor.def              ← NEW: Apptainer definition
├── run_simulation_cluster.sh    ← NEW: SLURM batch script
├── docs/
│   ├── TRANSLATION_GUIDE.md     ← NEW: How to translate PLC code
│   ├── SYSTEM_ANALYSIS.md       ← Existing: Reference analysis
│   ├── PLC_DOCUMENTATION.md     ← Existing: General PLC guide
│   └── ...
├── src/mock_up/
│   ├── components.py            ← Existing: Backbone components
│   ├── config.py                ← Existing: Parameters
│   └── ...
└── .gitignore                   ← UPDATED: Container artifacts
```

---

## Next Steps for Students

1. **Read Updated Getting Started**
   - [GETTING_STARTED.md](GETTING_STARTED.md)
   - Understand setup options
   - Choose deployment method

2. **Read Translation Guide**
   - [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md)
   - Understand scope and priorities
   - Learn translation workflow

3. **Set Up Environment**
   - Local: `python3 -m venv venv && ...`
   - Docker: `docker build -t ws-conveyor-twin .`
   - Cluster: Transfer .sif file

4. **Begin Translation**
   - Start with simplest component
   - Follow step-by-step workflow
   - Test incrementally

---

## Summary

**Files Added**: 4 new files (Dockerfile, ws_conveyor.def, run_simulation_cluster.sh, TRANSLATION_GUIDE.md)  
**Files Updated**: 2 files (GETTING_STARTED.md, .gitignore)  
**Lines Added**: ~1200 lines of documentation and configuration

**Key Improvements**:
- ✅ Three deployment options (local, Docker, cluster)
- ✅ Clear expectations about translation scope
- ✅ Explicit guidance on PLC → Python translation
- ✅ Acknowledgment of visual code (SFC diagrams)
- ✅ LLM usage guidance
- ✅ HPC cluster support for long simulations

**Status**: Ready for student use with flexible deployment options and clear translation guidance.

---

**Last Updated**: February 2026  
**Total Repository Files**: 36 (4 new since last update)
