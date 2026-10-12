"""Standard tracker-command contract and safe output sinks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Protocol

from project.config import MAX_TRACKER_TILT_DEG


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
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("timestamp must be a non-empty timezone-aware ISO 8601 string")
        try:
            parsed_timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("timestamp must be a valid timezone-aware ISO 8601 string") from error
        if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if not math.isfinite(self.tilt_offset_deg) or abs(self.tilt_offset_deg) > MAX_TRACKER_TILT_DEG:
            raise ValueError(
                f"tilt_offset_deg must be finite and between "
                f"-{MAX_TRACKER_TILT_DEG:g} and {MAX_TRACKER_TILT_DEG:g} degrees"
            )
        if self.tilt_deg is not None and (
            not math.isfinite(self.tilt_deg)
            or not -MAX_TRACKER_TILT_DEG <= self.tilt_deg <= MAX_TRACKER_TILT_DEG
        ):
            raise ValueError(
                f"tilt_deg must be finite and between "
                f"-{MAX_TRACKER_TILT_DEG:g} and {MAX_TRACKER_TILT_DEG:g} degrees"
            )


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
