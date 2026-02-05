# Repository Index & Quick Navigation

## Latest Updates (with Kod_WSConv_Sven2022 PDF)

✅ **SYSTEM ANALYSIS COMPLETE**: See [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) for detailed breakdown of the actual WS Conveyor system

✅ **COMPONENTS UPDATED**: [src/mock_up/components.py](src/mock_up/components.py) now includes:
- ConveyorMotor (speed control, ramps)
- TransferElevator (UP/DOWN positions)
- Buffer (2-pallet queue)
- DockingStation (6 stations with SFC)
- PneumaticSystem (pressure monitoring)
- RFIDReader (pallet tracking)

✅ **CONFIGURATION UPDATED**: [src/mock_up/config.py](src/mock_up/config.py) with WS Conveyor parameters:
- Conveyor: 0.18 m/s max, 20-100% speed, 2s ramp
- Elevator: 0.5s travel time
- Buffer: 2 pallet capacity
- Pneumatic: 6 bar target, 5.5-7.0 bar range
- RFID: 0.5s detection delay
- Stations: 6 docking stations (DS1-DS6)

✅ **EXAMPLE SIMULATION**: [examples/ws_conveyor_simulation.py](examples/ws_conveyor_simulation.py) demonstrates the actual system in action

---

## Quick Navigation by Purpose

### 🎓 Students Starting Here

1. **Understand the Project** (15 minutes)
   - Start: [README.md](README.md) — What is this project?
   - Then: [GETTING_STARTED.md](GETTING_STARTED.md) — Get environment running
   
2. **Learn About the System** (30 minutes)
   - Read: [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) — What you're building
   - Reference: [Kod_WSConv_Sven2022.pdf](docs/Kod_WSConv_Sven2022.pdf) — Original documentation
   
3. **Understand the Phases** (20 minutes)
   - Read: [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) — 8-14 week timeline
   - Track: [STUDENT_CHECKLIST.md](STUDENT_CHECKLIST.md) — Progress tracker
   
4. **Begin Phase 1** (Weeks 1-2)
   - Guide: [docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md) — How to analyze
   - Use: [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md) — Already analyzed for reference

---

## File Locations Quick Reference

**Key System Files**:
- System Documentation: [Kod_WSConv_Sven2022.pdf](docs/Kod_WSConv_Sven2022.pdf)
- System Analysis: [docs/SYSTEM_ANALYSIS.md](docs/SYSTEM_ANALYSIS.md)
- Components: [src/mock_up/components.py](src/mock_up/components.py)
- Configuration: [src/mock_up/config.py](src/mock_up/config.py)
- Example Sim: [examples/ws_conveyor_simulation.py](examples/ws_conveyor_simulation.py)

---

**Last Updated**: February 2026 with Kod_WSConv_Sven2022.pdf analysis
