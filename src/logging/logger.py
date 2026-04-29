# src/logging/logger.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


_LEVEL_RANK = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


class Logger:
    """Project JSONL logger with backward-compatible helper methods."""

    def __init__(
        self,
        path: str,
        level: str = "INFO",
        buffer_size: int = 200,
        append: bool = True,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.level = (level or "INFO").upper()
        self.buffer_size = max(int(buffer_size), 1)
        self.buffer: list[str] = []
        self.file = open(self.path, "a" if append else "w", encoding="utf-8")

    def _level_allowed(self, severity: str) -> bool:
        current = _LEVEL_RANK.get(self.level, _LEVEL_RANK["INFO"])
        event = _LEVEL_RANK.get((severity or "info").upper(), _LEVEL_RANK["INFO"])
        return event >= current

    def _normalize_timestamp(self, timestamp: Optional[datetime]) -> datetime:
        ts = timestamp or datetime.utcnow()
        # Keep existing repository convention: ISO + explicit Z suffix.
        return ts

    def log_event(
        self,
        event_type: str,
        component_id: str,
        event_name: Optional[str] = None,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Generic event entrypoint for current simulations/examples."""
        if not self._level_allowed(severity):
            return

        ts = self._normalize_timestamp(timestamp)
        event: Dict[str, Any] = {
            "timestamp": ts.isoformat() + "Z",
            "timestamp_seconds": ts.timestamp(),
            "event_type": event_type,
            "component_id": component_id,
            "severity": severity.lower(),
            "details": details or {},
        }
        if event_name is not None:
            event["event_name"] = event_name
        if sim_time_s is not None:
            event["sim_time_s"] = float(sim_time_s)
        if sim_time_hms is not None:
            event["sim_time_hms"] = sim_time_hms
        if extra:
            event.update(extra)
        self._write_event(event)

    def log_state_change(
        self,
        component_id: str,
        component_type: str,
        old_state: str,
        new_state: str,
        trigger: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
    ) -> None:
        """Record state transition."""
        self.log_event(
            event_type="state_change",
            component_id=component_id,
            event_name=f"{old_state}_{new_state}",
            severity="info",
            details=details,
            timestamp=timestamp,
            sim_time_s=sim_time_s,
            sim_time_hms=sim_time_hms,
            component_type=component_type,
            old_state=old_state,
            new_state=new_state,
            trigger=trigger,
        )

    def log_condition(
        self,
        component_id: str,
        condition_name: str,
        result: bool,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
    ) -> None:
        """Record gating/interlock checks."""
        self.log_event(
            event_type="condition_check",
            component_id=component_id,
            event_name=condition_name,
            severity="debug",
            details=details,
            timestamp=timestamp,
            sim_time_s=sim_time_s,
            sim_time_hms=sim_time_hms,
            result=bool(result),
        )

    def log_metric(
        self,
        component_id: str,
        event_name: str,
        details: Dict[str, Any],
        severity: str = "info",
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
    ) -> None:
        """Record metric sample."""
        self.log_event(
            event_type="performance_metric",
            component_id=component_id,
            event_name=event_name,
            severity=severity,
            details=details,
            timestamp=timestamp,
            sim_time_s=sim_time_s,
            sim_time_hms=sim_time_hms,
        )

    def log_error(
        self,
        component_id: str,
        error_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
    ) -> None:
        """Record warning/error events."""
        self.log_event(
            event_type="error",
            component_id=component_id,
            event_name=error_name,
            severity="error",
            details=details,
            timestamp=timestamp,
            sim_time_s=sim_time_s,
            sim_time_hms=sim_time_hms,
            message=message,
        )

    def log_snapshot(
        self,
        details: Dict[str, Any],
        component_id: str = "system_global",
        severity: str = "debug",
        timestamp: Optional[datetime] = None,
        sim_time_s: Optional[float] = None,
        sim_time_hms: Optional[str] = None,
    ) -> None:
        """Record state snapshot and flush immediately."""
        self.log_event(
            event_type="state_snapshot",
            component_id=component_id,
            severity=severity,
            details=details,
            timestamp=timestamp,
            sim_time_s=sim_time_s,
            sim_time_hms=sim_time_hms,
        )
        self.flush()

    def _write_event(self, event: Dict[str, Any]) -> None:
        self.buffer.append(json.dumps(event, ensure_ascii=False))
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        for line in self.buffer:
            self.file.write(line + "\n")
        self.buffer.clear()
        self.file.flush()

    def finalize(self) -> None:
        self.flush()
        if not self.file.closed:
            self.file.close()

    # context manager support
    def __enter__(self) -> "Logger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.finalize()