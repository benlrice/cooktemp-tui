"""Where readings come from: the radio probe through rtl_433, and a demo."""

import asyncio
import json
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


RADIO_PROBE_MODEL = "Thermopro-TP12"
RADIO_FIELDS = {"temperature_1_C": "radio_food", "temperature_2_C": "radio_pit"}
RETRY_MIN_SECONDS = 2.0
RETRY_MAX_SECONDS = 30.0


def parse_rtl433_line(line: str, now: float) -> list[Reading]:
    """Turn one line of `rtl_433 -F json` output into readings.

    Lines that are not JSON, or are from another device, give no readings.
    """
    try:
        message = json.loads(line)
    except ValueError:
        return []
    if not isinstance(message, dict) or message.get("model") != RADIO_PROBE_MODEL:
        return []
    readings = []
    for field, channel in RADIO_FIELDS.items():
        value = message.get(field)
        if isinstance(value, int | float):
            readings.append(Reading(channel, float(value), now))
    return readings


class RadioProbeSource:
    """Readings from the radio probe, read from a child `rtl_433` process.

    If rtl_433 stops (for example, the dongle is busy), it is started again
    after a delay that grows up to 30 seconds.
    """

    def __init__(self, rtl_433: str = "rtl_433") -> None:
        self.argv = [rtl_433, "-f", "433.92M", "-F", "json"]
        self.status = "starting rtl_433"

    async def readings(self) -> AsyncIterator[Reading]:
        delay = RETRY_MIN_SECONDS
        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *self.argv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except OSError as error:
                self.status = f"cannot start rtl_433: {error}"
            else:
                errors = asyncio.create_task(self._watch_errors(proc))
                try:
                    self.status = "listening on 433.92 MHz"
                    async for raw in proc.stdout:
                        delay = RETRY_MIN_SECONDS
                        line = raw.decode(errors="replace")
                        for reading in parse_rtl433_line(line, time.monotonic()):
                            yield reading
                finally:
                    errors.cancel()
                    if proc.returncode is None:
                        proc.terminate()
                    await proc.wait()
                self.status = f"rtl_433 stopped, retrying in {delay:.0f} s"
            await asyncio.sleep(delay)
            delay = min(delay * 2, RETRY_MAX_SECONDS)

    async def _watch_errors(self, proc: asyncio.subprocess.Process) -> None:
        """Keep the last line rtl_433 writes to stderr, to show the user."""
        async for raw in proc.stderr:
            line = raw.decode(errors="replace").strip()
            if line and "error" in line.lower():
                self.status = line
