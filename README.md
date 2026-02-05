# WS Conveyor System - Digital Twin Student Project

## System Description

This project develops a **digital twin of a modular workstation conveyor system** (Kod_WSConv_Sven2022) used in automated manufacturing. The system handles pallet transport, buffer management, and multi-station processing with pneumatic and RFID control.

**Key Components**:
- **Main Conveyor**: Variable-speed belt (20-100% = 0-0.18 m/s)
- **Transfer Elevator**: Moves pallets between queue and working height
- **Buffer Queue**: Holds up to 2 pallets awaiting processing
- **6 Docking Stations**: Process pallets with SFC state machines
- **Pneumatic System**: Pressure/flow monitoring (target 6 bar)
- **RFID Tracking**: Identifies pallets (8-byte tags, 0.5s detection)

## Project Aim

Automatically translate the **Kod_WSConv_Sven2022.pdf** PLC documentation into a verifiable Python digital twin. Run extended simulations to study system dynamics, throughput, reliability, and fault conditions.

## Key Objectives

1. **Analyze PLC Documentation** — Understand conveyor, elevator, buffer, stations, pneumatics, RFID
2. **Translate to Code** — Create Python components matching documented behavior
3. **Verify Logic** — Test that code faithfully reproduces documentation
4. **Build Simulator** — Implement event-driven simulation engine
5. **Log & Analyze** — Capture 24+ hour simulations and analyze patterns
6. **Optional: Extend** — Add ML-based anomaly detection (Phase 6)

## Repository Structure

```
drone-factory-digital-twin/
├── README.md                              # This file
├── SETUP.md                               # Environment setup guide
├── docs/
│   ├── PROJECT_PHASES.md                  # Detailed phase breakdown
│   ├── PLC_DOCUMENTATION.md               # System specification analysis guide
│   ├── ARCHITECTURE.md                    # System design & architecture
│   ├── LOGGING_SPECIFICATION.md           # Data logging format & standards
│   ├── VERIFICATION_CHECKLIST.md          # Verification methodology
│   └── SIMULATION_GUIDE.md                # Simulation execution & parameters
├── src/
│   ├── mock_up/                           # Python mock-up implementation
│   │   ├── __init__.py
│   │   ├── components.py                  # Individual system components
│   │   ├── state.py                       # Global system state management
│   │   ├── logic.py                       # PLC logic translation
│   │   ├── config.py                      # Configuration & parameters
│   │   └── utils.py                       # Utility functions
│   ├── digital_twin/                      # Enhanced twin implementation
│   │   ├── __init__.py
│   │   ├── twin.py                        # Main digital twin class
│   │   ├── events.py                      # Event system
│   │   └── adapters.py                    # Hardware/simulation adapters
│   ├── verification/                      # Verification mechanisms
│   │   ├── __init__.py
│   │   ├── validators.py                  # Logic validators
│   │   ├── test_cases.py                  # Test scenarios
│   │   └── conformance.py                 # Conformance checking
│   ├── simulation/                        # Simulation engine
│   │   ├── __init__.py
│   │   ├── simulator.py                   # Main simulator
│   │   ├── time_manager.py                # Virtual time management
│   │   ├── scheduler.py                   # Event scheduler
│   │   └── scenarios.py                   # Test scenarios
│   └── logging/                           # Logging framework
│       ├── __init__.py
│       ├── logger.py                      # Main logging system
│       ├── formatters.py                  # Output formatters (JSON, CSV, etc.)
│       └── parser.py                      # Log parsing & analysis tools
├── tests/
│   ├── unit/                              # Unit tests for components
│   ├── integration/                       # Integration tests
│   └── simulation/                        # Simulation validation tests
├── data/
│   ├── logs/                              # Simulation output logs
│   └── embeddings/                        # Optional: embeddings & vectors
├── analysis/
│   ├── notebooks/                         # Jupyter notebooks for data analysis
│   └── scripts/                           # Analysis scripts
├── tools/
│   ├── plc_parser.py                      # Tool to parse PLC documentation
│   ├── log_analyzer.py                    # Log analysis utility
│   └── visualization.py                   # Visualization tools
├── requirements.txt                       # Python dependencies
└── .gitignore
```

## Quick Start

### 1. Environment Setup
```bash
git clone <repo-url>
cd drone-factory-digital-twin
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

See [SETUP.md](docs/SETUP.md) for detailed setup instructions.

### 2. Understand the System
- Read [docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md) to understand how to analyze the original documentation
- Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system design approach
- Check [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) for the breakdown of work phases

### 3. Begin Implementation
Start with **Phase 1: Analysis & Translation**
- Analyze the provided PLC documentation (Kod_WSConv_Sven2022.pdf)
- Use tools in `tools/plc_parser.py` to help extract key logic
- Implement basic components in `src/mock_up/components.py`
- Follow the detailed guide in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### 4. Verify Your Implementation
- Write test cases in `tests/` folder
- Use verification tools in `src/verification/`
- Follow the checklist in [docs/VERIFICATION_CHECKLIST.md](docs/VERIFICATION_CHECKLIST.md)

### 5. Simulate & Analyze
- Run simulations using `src/simulation/simulator.py`
- Logs are saved to `data/logs/` in standardized formats
- Analyze results using notebooks in `analysis/notebooks/`

## Key Concepts

### Digital Twin
A digital twin is a virtual replica of a physical system that:
- Mirrors the actual system behavior
- Enables simulation and analysis without physical constraints
- Supports long-term studies and what-if scenarios
- Provides a foundation for verification and improvement

### PLC Logic Translation
The PLC (Programmable Logic Controller) documentation describes:
- State transitions and conditions
- Timing and sequencing
- Input/output mappings
- System interactions

**Automatic translation** means converting this into:
- Python classes representing components
- State machines for logic flow
- Event-driven simulation kernels
- Testable, maintainable code

### Simulation Horizon
This project focuses on **long-horizon simulations** (hours, days, or weeks of virtual time) to:
- Discover emergent behaviors
- Identify accumulating errors or drift
- Study system robustness
- Validate long-term predictions

### Logging & Analysis
Comprehensive logging captures:
- State changes (timestamp, component, old state, new state)
- Events (triggers, conditions, outcomes)
- Performance metrics (cycle times, throughput)
- Anomalies or deviations

Format: JSON (structured, queryable), CSV (analysis-friendly), or custom binary

## Technical Skills Required

- **Python** (core implementation)
- **System thinking** (understanding complex interactions)
- **Logic programming** (translating PLC into code)
- **Testing & verification** (ensuring correctness)
- **Data analysis** (optional: log analysis & visualization)
- **Simulation concepts** (event-driven, time management)

## Learning Resources

- See [docs/SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md) for simulation best practices
- See [docs/LOGGING_SPECIFICATION.md](docs/LOGGING_SPECIFICATION.md) for data format standards
- Example implementations in `src/` folder
- Unit tests in `tests/` demonstrate expected behavior

## Important Files to Review

1. **[docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md)** — Start here for project breakdown
2. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design decisions
3. **[docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md)** — How to analyze the source system
4. **[docs/LOGGING_SPECIFICATION.md](docs/LOGGING_SPECIFICATION.md)** — Data format standards

## Deliverables

By the end of the project, students should deliver:

✓ **Mock-up implementation** — Executable Python model of the drone factory  
✓ **Verification report** — Evidence that logic matches documentation  
✓ **Simulation logs** — Extended runs (≥24 hours virtual time) with systematic logging  
✓ **Analysis report** — System dynamics, interactions, deviations, insights  
✓ **Code documentation** — Inline comments, design decisions, usage guides  
✓ **Optional: Embedding analysis** — If implementing ML-based anomaly detection  

## Support & Questions

- Review the [docs/](docs/) folder for comprehensive guides
- Check example implementations in [src/](src/)
- Examine unit tests in [tests/](tests/) for usage patterns
- Consult [tools/](tools/) for parsing and analysis utilities

## License & Attribution

This is an educational project developed for system engineering courses.

---

**Next Step:** Read [SETUP.md](docs/SETUP.md) to set up your development environment, then go to [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) to understand the project timeline.
