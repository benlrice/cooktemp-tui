"""Where readings come from. Milestone 1 has only the demo source."""

import asyncio
import math
import time
from collections.abc import AsyncIterator
from typing import Protocol

from cooktemp_tui.model import CHANNELS, Reading


class Source(Protocol):
    def readings(self) -> AsyncIterator[Reading]: ...


def demo_celsius(channel: str, elapsed: float) -> float:
    """A smooth fake cook curve. `elapsed` is virtual seconds since the start."""
    if channel == "ble_food":
        return 20 + 80 * (1 - math.exp(-elapsed / 5400))
    if channel == "radio_food":
        return 22 + 78 * (1 - math.exp(-elapsed / 7200))
    if channel == "radio_pit":
        return 25 + 82 * (1 - math.exp(-elapsed / 600)) + 3 * math.sin(elapsed / 300)
    raise KeyError(channel)


class DemoSource:
    """Fake readings for every channel. `speed` makes the cook run faster."""

    def __init__(self, interval: float = 1.0, speed: float = 60.0) -> None:
        self.interval = interval
        self.speed = speed

    async def readings(self) -> AsyncIterator[Reading]:
        start = time.monotonic()
        while True:
            elapsed = (time.monotonic() - start) * self.speed
            for channel in CHANNELS:
                yield Reading(channel, demo_celsius(channel, elapsed), elapsed)
            await asyncio.sleep(self.interval)
