"""Standard tracker-command contract and safe output sinks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TrackerCommand:
    timestamp: str
    subzone_id: str
    tilt_offset_deg: float
    mode: str = "recommendation"
    reason: str = "dli_target"
    safety_state: str = "normal"
    tilt_deg: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.tilt_offset_deg):
            raise ValueError("tilt_offset_deg must be finite")
        if self.tilt_deg is not None and (not math.isfinite(self.tilt_deg) or not -90.0 <= self.tilt_deg <= 90.0):
            raise ValueError("tilt_deg must be finite and between -90 and 90 degrees")


def manual_tracker_command(
    *,
    timestamp: str,
    subzone_id: str,
    tilt_deg: float,
    reason: str = "manual_override",
) -> TrackerCommand:
    """Create an absolute-angle manual command for experiments or a flat position.

    ``tilt_deg`` is the physical tracker target relative to the configured
    horizontal zero, not an offset from the sun-following schedule. The command
    is intentionally still just a ``CommandSink`` message: ``DryRunCommandSink``
    and ``JsonlCommandSink`` are safe for simulation/replay, while a future
    hardware adapter can translate the same validated target into its protocol.
    """
    return TrackerCommand(
        timestamp=timestamp,
        subzone_id=subzone_id,
        tilt_offset_deg=0.0,
        tilt_deg=float(tilt_deg),
        mode="manual_override",
        reason=reason,
        safety_state="manual",
    )


class CommandSink(Protocol):
    def send(self, command: TrackerCommand) -> None: ...


class JsonlCommandSink:
    """Append commands to a file for review, replay, or later lab adaptation."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def send(self, command: TrackerCommand) -> None:
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(asdict(command), sort_keys=True) + "\n")


class DryRunCommandSink:
    """Collect commands without touching any hardware or network endpoint."""

    def __init__(self):
        self.commands: list[TrackerCommand] = []

    def send(self, command: TrackerCommand) -> None:
        self.commands.append(command)
