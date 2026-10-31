"""Where readings come from: the radio probe through rtl_433, and a demo."""

import asyncio
import json
import math
import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol

from chefstemp_ble.protocol import DeviceMessage

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


def reading_from_message(message: DeviceMessage, now: float) -> Reading | None:
    """The BLE food reading in a decoded frame, or None for other fields."""
    if not message.checksum_valid or message.temperature_celsius is None:
        return None
    return Reading("ble_food", float(message.temperature_celsius), now)


@asynccontextmanager
async def open_base(on_message: Callable[[DeviceMessage], None]):
    """Connect to the BLE base, deliver frames to `on_message`, and yield an
    event that is set when the connection is lost.

    The base allows one Bluetooth connection at a time, so this fails while
    the phone app is connected.
    """
    from bleak import BleakClient
    from chefstemp_ble.ble import find_device, subscribe

    address = await find_device()
    lost = asyncio.Event()
    async with BleakClient(address, disconnected_callback=lambda _: lost.set()) as client:
        await subscribe(client, on_message)
        yield lost


class BleBaseSource:
    """Readings from the BLE base. Reconnects with backoff if it drops."""

    def __init__(
        self,
        opener: Callable[
            [Callable[[DeviceMessage], None]], AbstractAsyncContextManager[asyncio.Event]
        ] = open_base,
    ) -> None:
        self.opener = opener
        self.status = "scanning for the BLE base"

    async def readings(self) -> AsyncIterator[Reading]:
        delay = RETRY_MIN_SECONDS
        while True:
            queue: asyncio.Queue[Reading] = asyncio.Queue()

            def on_message(message: DeviceMessage) -> None:
                reading = reading_from_message(message, time.monotonic())
                if reading is not None:
                    queue.put_nowait(reading)

            try:
                async with self.opener(on_message) as lost:
                    self.status = "connected to the BLE base"
                    delay = RETRY_MIN_SECONDS
                    while True:
                        getter = asyncio.create_task(queue.get())
                        dropped = asyncio.create_task(lost.wait())
                        done, pending = await asyncio.wait(
                            {getter, dropped}, return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in pending:
                            task.cancel()
                        if getter in done:
                            yield getter.result()
                        else:
                            break
                self.status = f"BLE base disconnected, retrying in {delay:.0f} s"
            except Exception as error:  # bleak raises many types; keep retrying
                self.status = f"BLE base: {error} (retrying in {delay:.0f} s)"
            await asyncio.sleep(delay)
            delay = min(delay * 2, RETRY_MAX_SECONDS)


class MergedSource:
    """Readings from several sources at once, in the order they arrive."""

    def __init__(self, *sources: Source) -> None:
        self.sources = sources

    async def readings(self) -> AsyncIterator[Reading]:
        queue: asyncio.Queue[Reading] = asyncio.Queue()

        async def pump(source: Source) -> None:
            async for reading in source.readings():
                queue.put_nowait(reading)

        tasks = [asyncio.create_task(pump(source)) for source in self.sources]
        try:
            while True:
                yield await queue.get()
        finally:
            for task in tasks:
                task.cancel()
