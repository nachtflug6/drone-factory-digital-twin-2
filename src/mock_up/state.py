# src/mock_up/state.py
"""System State Management

Maintains the global state of all components in the system.
Acts as the single source of truth for what's happening right now.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .config import SimulationConfig
from .components import create_ws_conveyor_system


class SystemState:
    """
    Global system state container.
    
    Tracks:
    - Current state of all components
    - System-level metrics
    - Consistency invariants
    
    Usage:
        config = SimulationConfig()
        system = SystemState(config)
        
        # Get a component
        motor = system.get_component('motor_1')
        
        # Update a component
        motor.state = MotorState.RUNNING
        
        # Get all components
        all_motors = system.get_components_by_type('motor')
    """
    
    def __init__(self, config: SimulationConfig):
        """Initialize system state from configuration"""
        self.config = config
        self.components: Dict[str, Any] = create_ws_conveyor_system(config)
        self.current_time: datetime = datetime.now()
        self.event_count: int = 0
    
    def get_component(self, component_id: str) -> Optional[Any]:
        """
        Get a component by ID
        
        Args:
            component_id: ID of component (e.g., 'motor_1')
        
        Returns:
            Component object or None if not found
        """
        return self.components.get(component_id)
    
    def get_components_by_type(self, component_type: str) -> List[Any]:
        """
        Get all components of a specific type
        
        Args:
            component_type: Type name (e.g., 'motor', 'conveyor')
        
        Returns:
            List of matching components
        """
        requested = component_type.lower().strip()
        aliases = {
            "motor": {"motor", "conveyormotor"},
            "conveyor": {"conveyor", "conveyormotor"},
            "rfid": {"rfid", "rfidreader"},
            "station": {"station", "dockingstation"},
        }
        accepted_names = aliases.get(requested, {requested})

        return [
            c
            for c in self.components.values()
            if c.__class__.__name__.lower() in accepted_names
        ]
    
    def register_component(self, component: Any) -> None:
        """
        Register a new component in the system
        
        Args:
            component: Component instance (must have 'id' attribute)
        """
        if not hasattr(component, 'id'):
            raise ValueError("Component must have 'id' attribute")
        
        self.components[component.id] = component
    
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get complete system state snapshot
        
        Returns:
            Dictionary with state of all components
            
        Usage:
            snapshot = system.get_snapshot()
            # Can serialize to JSON for logging
        """
        snapshot = {}
        for comp_id, component in self.components.items():
            if hasattr(component, '__dict__'):
                snapshot[comp_id] = {
                    k: str(v) if not isinstance(v, (int, float, bool, str)) else v
                    for k, v in component.__dict__.items()
                    if not k.startswith('_')
                }
        return snapshot
    
    def check_invariants(self) -> List[str]:
        """
        Check system consistency invariants
        
        Returns:
            List of violations (empty if all OK)
        
        Override this in subclasses to add domain-specific checks.
        """
        violations = []
        
        # Check 1: No component should be in two states simultaneously
        # (This is language-enforced for Enums, but worth checking)
        for comp_id, component in self.components.items():
            if hasattr(component, 'state'):
                if not isinstance(component.state, type(component.state).__bases__[0]):
                    violations.append(f"{comp_id}: Invalid state type")
        
        # Check 2: Component relationships
        # (Add domain-specific checks here)
        
        return violations
    
    def update(self, current_time: datetime) -> None:
        """
        Update system state for new time
        
        Call this periodically or when advancing time in simulation.
        
        Args:
            current_time: New current time
        """
        delta_seconds = max((current_time - self.current_time).total_seconds(), 0.0)
        self.current_time = current_time

        # Update components that have time-dependent behavior.
        # Components in this project use elapsed seconds, but legacy callers
        # may still pass absolute timestamps into SystemState.update.
        for component in self.components.values():
            if hasattr(component, 'update'):
                elapsed_seconds = self._get_component_elapsed_time(component, current_time, delta_seconds)
                component.update(elapsed_seconds)
            
            # Check invariants (e.g., load limits)
            if hasattr(component, 'check_load'):
                component.check_load()

    def _get_component_elapsed_time(
        self, component: Any, current_time: datetime, fallback_delta_seconds: float
    ) -> float:
        """Derive elapsed seconds expected by component.update()."""
        for attr in ("transition_start_time", "detect_start_time", "transfer_start_time"):
            started_at = getattr(component, attr, None)
            if isinstance(started_at, datetime):
                raw = (current_time - started_at).total_seconds()
                # datetime.now() markers vs virtual current_time => negative raw. Snap marker to
                # this frame so subsequent updates see cumulative (current_time - started_at).
                if raw < 0:
                    setattr(component, attr, current_time)
                    return 0.0
                return raw
        return fallback_delta_seconds
    
    def log_state(self) -> Dict[str, Any]:
        """
        Return state in a format suitable for logging
        
        Returns:
            Dictionary with timestamp and all component states
        """
        return {
            'timestamp': self.current_time.isoformat() + 'Z',
            'components': self.get_snapshot(),
            'event_count': self.event_count
        }


def create_system(config: SimulationConfig) -> SystemState:
    """
    Convenience function to create a new system state
    
    Args:
        config: Simulation configuration
    
    Returns:
        Initialized SystemState object
    """
    return SystemState(config)
