# Development Environment Setup Guide

## Prerequisites

- Python 3.9 or higher
- Git
- A code editor (VS Code recommended)
- 2+ GB disk space for simulations and logs
- Virtual environment tool (included with Python)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd drone-factory-digital-twin
```

## Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Key Dependencies

- **numpy** — Numerical computations
- **pandas** — Data analysis and logging
- **matplotlib** — Visualization
- **pytest** — Unit testing
- **pydantic** — Configuration validation
- **dataclasses-json** — JSON serialization
- **scipy** — Scientific computing (for analysis)

## Step 4: Verify Installation

```bash
# Test imports
python -c "import mock_up; import digital_twin; import simulation; print('✓ All modules imported successfully')"

# Run tests (basic sanity check)
pytest tests/ -v --tb=short
```

## Step 5: Explore the Project Structure

```bash
# Navigate project folders
ls -la                          # View repo structure
cat docs/PROJECT_PHASES.md      # Read project phases
cat docs/ARCHITECTURE.md        # Review system architecture
```

## Recommended IDE Setup (VS Code)

### Extensions to Install

1. **Python** (Microsoft) — Essential for Python development
2. **Pylance** — Advanced type checking
3. **Pytest** — Test runner integration
4. **Jupyter** — Notebook support for analysis
5. **GitLens** — Git integration

### Workspace Settings (`.vscode/settings.json`)

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

## Project Configuration

### Key Config File: `src/mock_up/config.py`

Edit this file to configure:
- System parameters (cycle times, thresholds)
- Component count and capacity
- Simulation runtime settings
- Logging verbosity

### Logging Configuration

Logs are written to `data/logs/` by default. Configure output format in:
- `src/logging/formatters.py` — Output format (JSON, CSV, etc.)
- `src/logging/logger.py` — Logging levels and filters

## Running Your First Simulation

```bash
# Simple test simulation
python -c "
from simulation.simulator import Simulator
from mock_up.config import SimulationConfig

config = SimulationConfig(simulation_time=3600)  # 1 hour
simulator = Simulator(config)
simulator.run()
print('✓ Simulation completed')
"
```

For detailed simulation instructions, see [docs/SIMULATION_GUIDE.md](SIMULATION_GUIDE.md).

## Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Pytest Not Found
```bash
# Install test dependencies explicitly
pip install pytest pytest-cov
```

### Python Version Issues
```bash
# Check Python version
python --version  # Should be 3.9+

# Use python3 explicitly if needed
python3 -m venv venv
python3 -m pip install -r requirements.txt
```

### Permission Issues (Linux/macOS)
```bash
# Make scripts executable
chmod +x scripts/*.py
chmod +x tools/*.py
```

## Development Workflow

### 1. Before Starting Work
```bash
# Activate environment
source venv/bin/activate

# Update dependencies (if needed)
pip install -r requirements.txt
```

### 2. Write Code
- Implement in `src/` folder
- Follow PEP 8 style guide
- Add docstrings to functions/classes
- Include type hints

### 3. Write Tests
- Create tests in `tests/` folder
- Test structure mirrors `src/` structure
- Run tests frequently:
  ```bash
  pytest tests/ -v
  pytest tests/ --cov=src  # With coverage
  ```

### 4. Run Simulations
```bash
python src/simulation/simulator.py
# Or use your custom simulation script
```

### 5. Analyze Results
```bash
# Notebooks in analysis/notebooks/
jupyter notebook analysis/notebooks/
```

## Managing Dependencies

### Adding New Packages
```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Dependency Structure

**Core Dependencies** (essential):
- numpy, pandas, matplotlib

**Optional Dependencies** (for specific phases):
- scikit-learn (for embeddings/ML)
- plotly (for interactive visualizations)
- h5py (for large log files)

## Best Practices

✓ **Always work in virtual environment**  
✓ **Commit clean, working code**  
✓ **Write tests for new components**  
✓ **Document design decisions**  
✓ **Keep logs organized by date/simulation**  
✓ **Review similar implementations before coding**  

## Next Steps

1. ✅ **Environment ready?** → Read [docs/PROJECT_PHASES.md](PROJECT_PHASES.md)
2. 📖 **Understand the system?** → Read [docs/ARCHITECTURE.md](ARCHITECTURE.md)
3. 🔍 **Analyze documentation?** → Read [docs/PLC_DOCUMENTATION.md](PLC_DOCUMENTATION.md)
4. 💻 **Start coding?** → Begin Phase 1 in [docs/PROJECT_PHASES.md](PROJECT_PHASES.md)

## Support

- Check the [README.md](../README.md) for general project overview
- Review existing code in `src/` folder for examples
- Run tests to see expected behavior: `pytest tests/ -v`
- Check inline code comments for implementation details
