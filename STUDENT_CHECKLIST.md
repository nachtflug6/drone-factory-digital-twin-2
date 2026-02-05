# STUDENT_CHECKLIST.md

# Student Project Checklist - Drone Factory Digital Twin

Use this checklist to track your progress through the project. Check off items as you complete them.

---

## Phase 1: System Analysis & Documentation Review (Weeks 1-2)

### Understanding the System
- [ ] I have read the introduction to the project (README.md)
- [ ] I have read the project phases overview (docs/PROJECT_PHASES.md)
- [ ] I understand what a digital twin is and why it matters
- [ ] I understand the project timeline (8-14 weeks total)

### Analyzing PLC Documentation
- [ ] I have reviewed the provided PLC documentation (Kod_WSConv_Sven2022.pdf)
- [ ] I have read the analysis guide (docs/PLC_DOCUMENTATION.md)
- [ ] I have created a list of all major system components
- [ ] I have identified component inputs and outputs
- [ ] I have documented state machines for key components
- [ ] I have extracted timing constraints from documentation
- [ ] I have mapped inter-component dependencies

### Design Documentation
- [ ] I have read the architecture guide (docs/ARCHITECTURE.md)
- [ ] I have sketched component hierarchy on paper or digitally
- [ ] I have documented the overall system architecture
- [ ] I have identified any ambiguities or conflicts in documentation
- [ ] I have flagged assumptions I'm making (with explanations)
- [ ] I have discussed ambiguities with team/instructor

### Team Agreement
- [ ] Our team agrees on the architecture approach
- [ ] We have consensus on component representations
- [ ] We have agreed on naming conventions
- [ ] We have assigned Phase 2 work tasks

### Deliverable: System Analysis Document
- [ ] Created file: `docs/SYSTEM_ANALYSIS.md` (or similar)
- [ ] Document includes: component list, state machines, timing, dependencies
- [ ] Document is reviewed and approved

---

## Phase 2: Mock-up Implementation (Weeks 3-5)

### Component Implementation
- [ ] I have read the example components in src/mock_up/components.py
- [ ] I have implemented Component 1 (State Enum + dataclass)
- [ ] I have implemented Component 2
- [ ] I have implemented Component 3
- [ ] [List all other components as checkboxes]
- [ ] All components have complete docstrings
- [ ] All state names match documentation exactly (case-sensitive!)
- [ ] All component parameters are documented

### State Management
- [ ] I have reviewed src/mock_up/state.py
- [ ] I understand how SystemState tracks all components
- [ ] SystemState initializes all components correctly
- [ ] I can retrieve components by ID
- [ ] I can retrieve components by type
- [ ] Snapshot functionality works

### Logic Implementation
- [ ] I have reviewed src/mock_up/logic.py and example patterns
- [ ] I have implemented transition logic for Component 1
- [ ] I have implemented transition logic for Component 2
- [ ] [All components covered]
- [ ] All logic functions are well-documented
- [ ] Logic functions have clear condition comments
- [ ] Timing constraints are implemented correctly

### Configuration
- [ ] I have reviewed src/mock_up/config.py
- [ ] All timing constants are externalized to config
- [ ] All component parameters are in config
- [ ] Config can be easily modified without changing code
- [ ] Default values match documentation

### Code Quality
- [ ] Code passes: `python -m py_compile src/mock_up/*.py`
- [ ] No syntax errors when importing: `python -c "import src.mock_up"`
- [ ] All functions have docstrings
- [ ] Type hints are used consistently
- [ ] PEP 8 style is followed (spaces, naming, etc.)

### Testing Basic Implementation
- [ ] Run basic_simulation.py and it completes without errors
- [ ] All components are created and initialized
- [ ] Component states can be read and modified
- [ ] No crashes during initialization

### Code Review
- [ ] Team review of all components completed
- [ ] Feedback integrated
- [ ] Design decisions documented

---

## Phase 3: Verification & Testing (Weeks 6-7)

### Unit Tests - Component Coverage
- [ ] Created: tests/unit/test_[component].py for each component type
- [ ] Test: Initial state is correct
- [ ] Test: Each documented transition works
- [ ] Test: Invalid transitions are blocked
- [ ] Test: Timing constraints are honored
- [ ] Test: Edge cases (zero values, max values, etc.)
- [ ] Achieved test coverage: >80% of component code

### Unit Tests - Logic Coverage
- [ ] Created: tests/unit/test_logic.py
- [ ] Test: Each logic function with valid inputs
- [ ] Test: Each logic function with invalid inputs
- [ ] Test: Boundary conditions
- [ ] Test: Inter-component dependencies

### Integration Tests
- [ ] Created: tests/integration/test_[subsystem].py
- [ ] Test: Components interacting correctly
- [ ] Test: Cascading effects (A→B→C)
- [ ] Test: Synchronization between components
- [ ] Test: Error propagation

### Running Tests
- [ ] All unit tests pass: `pytest tests/unit/ -v`
- [ ] All integration tests pass: `pytest tests/integration/ -v`
- [ ] Generated coverage report: `pytest --cov=src/mock_up`
- [ ] Coverage is ≥80%

### Verification Against Documentation
- [ ] Created: `VERIFICATION_REPORT.md`
- [ ] Checklist: All documented behaviors tested
- [ ] Checklist: All timing constraints verified
- [ ] Checklist: All state transitions validated
- [ ] Documented any deviations from documentation
- [ ] Explained assumptions made

### Code Quality Review
- [ ] All tests have clear docstrings
- [ ] Test names describe what they test
- [ ] No code duplication in tests
- [ ] Test fixtures are properly organized

---

## Phase 4: Simulation & Logging (Weeks 8-9)

### Simulator Framework
- [ ] Reviewed: docs/SIMULATION_GUIDE.md
- [ ] Created: src/simulation/simulator.py (basic structure)
- [ ] Implemented: Time management (virtual clock)
- [ ] Implemented: Event queue/scheduler
- [ ] Implemented: Main simulation loop
- [ ] Implemented: State update cycle

### Logging Framework
- [ ] Reviewed: docs/LOGGING_SPECIFICATION.md
- [ ] Created: src/logging/logger.py
- [ ] Implemented: JSON logging (JSONL format)
- [ ] Implemented: Event logging for state changes
- [ ] Implemented: Condition logging (debug level)
- [ ] Implemented: Error/warning logging
- [ ] Implemented: Optional CSV format

### Running Simulations
- [ ] Basic 1-hour simulation runs without errors
- [ ] Logs are created in data/logs/ directory
- [ ] Logs are properly formatted (valid JSON)
- [ ] Simulation completes deterministically (same seed = same results)
- [ ] Ran 24-hour simulation successfully
- [ ] Logs for 24-hour run are saved and parseable

### Log Validation
- [ ] All log entries have timestamps
- [ ] Timestamps are monotonically increasing
- [ ] No duplicate events at same time
- [ ] All required fields present
- [ ] Events match documented state transitions

### Extended Simulations
- [ ] 24-hour simulation: Completed and logged
- [ ] 48-hour simulation: Completed and logged
- [ ] 1-week simulation: Completed and logged
- [ ] Logs are organized in data/logs/ by date

---

## Phase 5: Analysis & System Dynamics (Weeks 10-13)

### Log Parsing & Loading
- [ ] Created: src/logging/parser.py
- [ ] Can parse JSONL log files
- [ ] Can load into pandas DataFrames
- [ ] Can filter by component, event type, time range

### Data Analysis
- [ ] Created: analysis/notebooks/01_system_dynamics.ipynb
- [ ] Analyzed: State distribution per component
- [ ] Analyzed: State transition frequencies
- [ ] Analyzed: Timing of transitions (mean, std dev)
- [ ] Calculated: System performance metrics
  - Throughput (items/hour)
  - Cycle times
  - Utilization rates
  - Error frequencies

### Visualization
- [ ] Created plots showing:
  - Timeline of component states over time
  - Transition count per component
  - State duration distributions
  - System performance over time
  - Interaction patterns between components
- [ ] Plots are saved to analysis/plots/
- [ ] Plots have clear titles and axes labels

### Anomaly & Pattern Detection
- [ ] Identified repeating patterns in system behavior
- [ ] Found any deviations from expected behavior
- [ ] Documented unusual edge cases
- [ ] Analyzed error conditions and their recovery

### Analysis Report
- [ ] Created: ANALYSIS_REPORT.md
- [ ] Executive summary of findings
- [ ] System dynamics discovered
- [ ] Performance characteristics
- [ ] Deviations from documentation
- [ ] Recommendations for system improvement
- [ ] Conclusions and lessons learned

### Reproducibility
- [ ] All analysis can be run from scratch
- [ ] All data, code, and results are version controlled
- [ ] Instructions for reproducing analysis included

---

## Phase 6 (Optional): Embeddings & ML Analysis (Weeks 14+)

### Feature Engineering
- [ ] Designed feature vectors from log events
- [ ] Features capture: timing, state patterns, anomalies
- [ ] Features are normalized and scaled

### Embedding Generation
- [ ] Trained or applied embedding model
- [ ] Generated vector representations of system windows
- [ ] Stored embeddings in data/embeddings/

### Anomaly Detection
- [ ] Implemented similarity search over embeddings
- [ ] Developed anomaly detection using clustering/thresholds
- [ ] Applied to historical logs to find unusual patterns

### ML Analysis Report
- [ ] Created: ML_ANALYSIS_REPORT.md
- [ ] Documented embedding methodology
- [ ] Results of anomaly detection
- [ ] Novel insights from ML analysis
- [ ] Implications for system health/monitoring

---

## Final Deliverables

### Code Quality
- [ ] All code follows PEP 8 style guide
- [ ] All functions have docstrings
- [ ] No hardcoded values (use config.py)
- [ ] No commented-out code (clean up or document)
- [ ] Code is well-organized and readable

### Documentation
- [ ] README.md is complete and accurate
- [ ] docs/ folder has all guides
- [ ] ARCHITECTURE.md describes design
- [ ] All assumptions are documented
- [ ] All deviations from documentation are explained

### Version Control
- [ ] All code is in git repository
- [ ] Commits have clear messages
- [ ] Branch history is clean
- [ ] No accidental commits of large files or secrets

### Testing & Verification
- [ ] Unit tests cover >80% of code
- [ ] All tests pass
- [ ] Verification report is complete
- [ ] Reproducibility verified

### Simulation & Analysis
- [ ] Extended simulations (≥24 hours) completed
- [ ] Logs are clean and complete
- [ ] Analysis notebooks are functional
- [ ] Visualizations are clear and accurate
- [ ] Analysis report is thorough

### Presentation
- [ ] Team presentation prepared
- [ ] Live demo of simulation works
- [ ] Key findings are highlighted
- [ ] Limitations and future work discussed

---

## Team Coordination

### Communication
- [ ] Team meets regularly (weekly check-ins)
- [ ] Progress is tracked and shared
- [ ] Blockers are discussed promptly
- [ ] Code reviews happen before merging

### Code Sharing
- [ ] Git workflow is established
- [ ] Main branch is stable
- [ ] Feature branches for major changes
- [ ] Pull requests have clear descriptions

### Documentation
- [ ] Design decisions are documented
- [ ] Assumptions are listed
- [ ] Known issues are tracked
- [ ] Future improvements are noted

---

## Submission Checklist

Before submitting, verify:

- [ ] All code is committed and pushed
- [ ] README.md is complete
- [ ] ARCHITECTURE.md describes your design
- [ ] VERIFICATION_REPORT.md documents testing
- [ ] ANALYSIS_REPORT.md documents findings
- [ ] All test files exist in tests/
- [ ] All simulation logs are saved in data/logs/
- [ ] examples/basic_simulation.py runs without errors
- [ ] No Python errors: `python -m py_compile src/**/*.py`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Presentation is ready
- [ ] Team roles and contributions are documented

---

## Success Criteria

Your project is complete when:

✓ Mock-up implementation matches documented behavior  
✓ Test suite validates all functionality (>80% coverage)  
✓ Extended simulations run deterministically  
✓ Logs are complete and properly formatted  
✓ Analysis reveals system dynamics and patterns  
✓ All code is documented and reviewed  
✓ Final report documents findings and conclusions  

---

## Tips for Success

1. **Start early** — Don't wait until the last week to start writing code
2. **Test frequently** — Write tests as you implement components
3. **Document as you go** — Explaining code helps you understand it better
4. **Iterate** — First version won't be perfect; refine based on testing
5. **Communicate** — Ask questions when something is unclear
6. **Review code** — Learn from team members' implementations
7. **Commit often** — Small, frequent commits are easier to track
8. **Verify early** — Don't wait until Phase 5 to check your logic against docs

---

**Questions?** Check [docs/](docs/) folder or ask during team meetings.

**Ready to start?** Begin with [docs/PROJECT_PHASES.md](docs/PROJECT_PHASES.md) Phase 1.

Good luck! 🚀
