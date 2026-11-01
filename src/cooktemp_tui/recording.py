"""Write every reading to a file, and play a past cook back from one.

A cook file has one JSON object per line:
{"elapsed": 12.5, "wall": "2026-11-01T09:00:12", "channel": "ble_food", "celsius": 52.0}
`elapsed` is seconds since the cook started. Replay uses it to keep the timing.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import IO

from cooktemp_tui.model import Reading
from cooktemp_tui.sources import Source


def default_log_path(directory: Path = Path(".")) -> Path:
    return directory / time.strftime("cook-%Y%m%d-%H%M%S.jsonl")


class LoggingSource:
    """Passes readings through and writes each one to a cook file."""

    def __init__(self, source: Source, path: Path) -> None:
        self.source = source
        self.path = path

    async def readings(self) -> AsyncIterator[Reading]:
        start = time.monotonic()
        with self.path.open("a", encoding="utf-8") as file:
            async for reading in self.source.readings():
                write_reading(file, reading, time.monotonic() - start)
                yield reading


def write_reading(file: IO[str], reading: Reading, elapsed: float) -> None:
    record = {
        "elapsed": round(elapsed, 3),
        "wall": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "channel": reading.channel,
        "celsius": reading.celsius,
    }
    file.write(json.dumps(record) + "\n")
    file.flush()


def read_cook(path: Path) -> list[tuple[float, Reading]]:
    """Load a cook file as (elapsed, reading) pairs. Bad lines are skipped."""
    cook = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            elapsed = float(record["elapsed"])
            reading = Reading(record["channel"], float(record["celsius"]), elapsed)
        except (ValueError, KeyError, TypeError):
            continue
        cook.append((elapsed, reading))
    cook.sort(key=lambda pair: pair[0])
    return cook


class ReplaySource:
    """Plays a cook file back with its original timing, `speed` times faster.

    The source stops at the end of the file.
    """

    def __init__(self, path: Path, speed: float = 1.0) -> None:
        self.cook = read_cook(path)
        self.speed = speed

    async def readings(self) -> AsyncIterator[Reading]:
        previous = 0.0
        for elapsed, reading in self.cook:
            await asyncio.sleep(max(elapsed - previous, 0.0) / self.speed)
            previous = elapsed
            yield reading
