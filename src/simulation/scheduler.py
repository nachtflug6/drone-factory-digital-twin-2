# src/simulation/scheduler.py
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any, Callable, List, Optional, Tuple


@dataclass(order=True)
class ScheduledEvent:
    """Simulation-time event compatible with current float-based timeline."""

    due_sim_time_s: float
    priority: int
    name: str = field(compare=False)
    handler: Callable[..., Any] = field(compare=False)
    args: Tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)

    def execute(self) -> Any:
        return self.handler(*self.args, **self.kwargs)


class EventScheduler:
    """Min-heap scheduler used by optional event-driven simulations."""

    def __init__(self) -> None:
        self._queue: List[ScheduledEvent] = []
        self._seq = 0

    def schedule(
        self,
        due_sim_time_s: float,
        name: str,
        handler: Callable[..., Any],
        *args: Any,
        priority: int = 100,
        **kwargs: Any,
    ) -> None:
        ev = ScheduledEvent(
            due_sim_time_s=float(due_sim_time_s),
            priority=int(priority) * 1_000_000 + self._seq,
            name=name,
            handler=handler,
            args=tuple(args),
            kwargs=kwargs,
        )
        self._seq += 1
        heapq.heappush(self._queue, ev)

    def pop_next(self) -> Optional[ScheduledEvent]:
        if not self._queue:
            return None
        return heapq.heappop(self._queue)

    def peek_next(self) -> Optional[ScheduledEvent]:
        if not self._queue:
            return None
        return self._queue[0]

    def is_empty(self) -> bool:
        return not self._queue

    def __len__(self) -> int:
        return len(self._queue)