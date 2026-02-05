# PROJECT_OVERVIEW.md

# Drone Factory Digital Twin - Project Overview

## What is This Project?

You will build a **digital twin** — a virtual replica of a real drone factory that:
- Executes system logic from documentation
- Simulates months of operation in hours
- Allows safe experimentation and analysis
- Reveals system dynamics and patterns

## The Challenge

Modern factories are complex cyber-physical systems with dozens of interacting components. **Understanding their behavior is hard because:**

1. ❌ Real systems can't be easily interrupted or modified
2. ❌ Small inconsistencies accumulate over time
3. ❌ Long-term behavior is hard to predict
4. ❌ Experimentation is expensive and risky

**Your solution:** Build a digital twin that is:
- ✓ Safe to experiment with
- ✓ Fast to simulate (24 hours in <1 hour)
- ✓ Observable (log everything)
- ✓ Verifiable (prove it matches reality)

## The Workflow

```
Documentation         Python Code        Simulation        Analysis
     (PDF)         (components,         (execute &       (patterns,
                    logic, state)       log behavior)    insights)
       │                 │                   │               │
       │                 │                   │               │
       ▼                 ▼                   ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Read PLC   │  │  Implement   │  │   Run 24+hr  │  │   Analyze    │
│   Docs       │→ │  Components  │→ │  Simulation  │→ │   Logs &     │
│              │  │   & Logic    │  │   & Logging  │  │   Visualize  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
   Phase 1            Phase 2            Phase 4           Phase 5
  (1-2 weeks)       (2-3 weeks)        (1-2 weeks)       (2-3 weeks)
                                                           + Phase 3
                                                         (1-2 weeks)
                                                          Verification
```

## Key Questions You'll Answer

1. **Does your implementation match the documentation?**
   - Phase 3: Verification & Testing

2. **What happens over extended operation?**
   - Phase 4: Run 24+ hour simulations

3. **What patterns emerge from long-term behavior?**
   - Phase 5: Analyze logs and visualize results

4. **Are there anomalies or deviations?**
   - Phase 5: Find unusual patterns

5. **Could this predict real system issues?** (Optional: Phase 6)
   - Use ML embeddings for anomaly detection

## Success Looks Like

```
WEEK 1-2: System Analysis
├─ Components identified and documented
├─ State machines drawn for each
├─ Timing constraints extracted
└─ Architecture agreed upon

WEEK 3-5: Implementation
├─ All components implemented in Python
├─ Logic rules encoded
├─ Configuration externalized
└─ Basic imports work

WEEK 6-7: Verification
├─ >80% test coverage achieved
├─ All tests passing
├─ Behavior matches documentation
└─ Deviations documented

WEEK 8-9: Simulation
├─ Simulator runs without errors
├─ Deterministic (same seed = same result)
├─ Logs generated in standard format
└─ Extended runs complete successfully

WEEK 10-13: Analysis
├─ Logs parsed and loaded into DataFrames
├─ Patterns visualized
├─ System dynamics understood
└─ Report written with findings

WEEK 14+ (Optional): ML Analysis
├─ Features engineered from logs
├─ Embeddings generated
├─ Anomalies detected
└─ Advanced insights gained
```

## Repository Contents

### Documentation
- **README.md** — Start here! Project overview
- **GETTING_STARTED.md** — Quick 5-minute setup
- **docs/PROJECT_PHASES.md** — Detailed timeline
- **docs/ARCHITECTURE.md** — Design patterns & principles
- **docs/PLC_DOCUMENTATION.md** — How to analyze source docs
- **docs/SIMULATION_GUIDE.md** — How to build simulator
- **docs/LOGGING_SPECIFICATION.md** — Data format standards
- **docs/VERIFICATION_CHECKLIST.md** — Testing methodology

### Starter Code
- **src/mock_up/components.py** — Example component classes (START HERE!)
- **src/mock_up/state.py** — System state management
- **src/mock_up/logic.py** — Control logic template
- **src/mock_up/config.py** — Configuration parameters
- **examples/basic_simulation.py** — Runnable example
- **tests/unit/test_motor.py** — Example unit tests

### Your Work
- **src/** — Implementation folder (you code here)
- **tests/** — Test folder (write tests as you code)
- **data/logs/** — Simulation outputs go here
- **analysis/notebooks/** — Jupyter notebooks for analysis
- **STUDENT_CHECKLIST.md** — Track your progress

## How This Teaches You

| Phase | What You Learn | Skills Developed |
|-------|---|---|
| 1 | Analyze complex systems | System thinking, documentation review |
| 2 | Translate requirements to code | Software design, Python programming |
| 3 | Ensure correctness | Testing, verification, debugging |
| 4 | Build simulation engines | Event-driven systems, timing |
| 5 | Understand system behavior | Data analysis, visualization, insight |
| 6 | Apply advanced techniques | ML, anomaly detection, embeddings |

## Real-World Relevance

These skills are valuable in:

- 🏭 **Manufacturing** — Production system simulation & optimization
- 🤖 **Robotics** — Behavior verification & planning
- 🚗 **Autonomous Systems** — Safety validation
- 🏥 **Medical Devices** — Regulatory compliance & testing
- 🔐 **Cybersecurity** — System behavior analysis
- 📊 **Data Science** — Time-series analysis & anomaly detection

## How to Use This Repository

### As a Student:
1. Read **[GETTING_STARTED.md](GETTING_STARTED.md)** (5 minutes)
2. Run **[examples/basic_simulation.py](examples/basic_simulation.py)** (verify setup)
3. Read **[docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md)** (understand timeline)
4. Analyze **Kod_WSConv_Sven2022.pdf** (your source material)
5. Implement Phase 1 tasks using **[docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md)**
6. Use **[STUDENT_CHECKLIST.md](STUDENT_CHECKLIST.md)** to track progress

### As an Instructor:
- Modify **src/mock_up/components.py** to match your actual system
- Adjust **docs/PROJECT_PHASES.md** timeline to your course
- Customize **examples/basic_simulation.py** to your needs
- Use **tests/** as assessment rubric

## Project Architecture (5-Minute Overview)

```
┌─────────────────────────────────────────────────┐
│  Simulator (orchestrates virtual time)          │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌────────────┐  ┌────────────┐                │
│  │ Components │  │   Logic    │                │
│  │ (Motors,   │  │ (PLC rules)│                │
│  │ Conveyors) │  │            │                │
│  └────────────┘  └────────────┘                │
│         △               △                       │
│         └───────┬───────┘                       │
│                 │                               │
│         ┌───────▼────────┐                     │
│         │  SystemState   │                     │
│         │  (keeps track) │                     │
│         └────────────────┘                     │
│                 │                               │
│         ┌───────▼────────┐                     │
│         │    Logger      │                     │
│         │  (records all) │                     │
│         └────────────────┘                     │
│                 │                               │
│                 ▼                               │
│           data/logs/...                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Key Technologies

- **Python 3.9+** — Main language
- **Pytest** — Testing framework
- **Pandas** — Data analysis
- **Matplotlib** — Visualization
- **JSON/CSV** — Data formats
- **Git** — Version control

## Common Questions

**Q: How much Python experience do I need?**
A: Intermediate level. You should be comfortable with classes, functions, and basic OOP.

**Q: What if I don't understand the PLC documentation?**
A: Start with [docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md) for a guide. Ask for clarification!

**Q: Can I work solo or in a team?**
A: Either! The project is designed for 1-4 person teams (larger teams = bigger system model).

**Q: How long will this take?**
A: 8-14 weeks, depending on system complexity and team size. Plan 10-15 hours/week.

**Q: What if I get stuck?**
A: Check [docs/](docs/) first (most answers are there), ask your team, then ask instructor.

**Q: Can I extend this project?**
A: Yes! Phase 6 (ML embeddings) and beyond are open-ended exploration.

## Let's Get Started! 🚀

### Step 1: Setup (5 minutes)
→ Read **[GETTING_STARTED.md](GETTING_STARTED.md)**

### Step 2: Understand Timeline (10 minutes)
→ Read **[docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md)**

### Step 3: Begin Phase 1 (1-2 weeks)
→ Read **[docs/PLC_DOCUMENTATION.md](docs/PLC_DOCUMENTATION.md)**

### Step 4: Implement Phase 2 (2-3 weeks)
→ Edit **[src/mock_up/components.py](src/mock_up/components.py)**

### Step 5: Test & Verify (1-2 weeks)
→ Write tests in **[tests/](tests/)**

### Step 6: Build Simulator (1-2 weeks)
→ Read **[docs/SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md)**

### Step 7: Analyze Results (2-3 weeks)
→ Create notebooks in **[analysis/notebooks/](analysis/notebooks/)**

---

## Project Structure at a Glance

```
Your Mission:
  Documentation → Components → Tests → Simulator → Analysis

Our Support:
  Guides (docs/) + Examples (src/, examples/) + Checklist (STUDENT_CHECKLIST.md)

Your Success:
  Working mock-up + Complete tests + Extended simulations + Findings
```

---

**Ready?** Start with **[GETTING_STARTED.md](GETTING_STARTED.md)**

Questions? Check **[docs/](docs/)** or ask your instructor/team.

Good luck! 🎯
