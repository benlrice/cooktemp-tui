import sys

from cooktemp_tui.model import Reading
from cooktemp_tui.sources import (
    BleBaseSource,
    MergedSource,
    RadioProbeSource,
    parse_rtl433_line,
    reading_from_message,
)

TP12 = '{"model":"Thermopro-TP12","id":57,"temperature_1_C":20.2,"temperature_2_C":320.0,"mic":"CRC"}'


def test_tp12_line_gives_food_and_pit_readings():
    readings = parse_rtl433_line(TP12, now=5.0)
    assert [(r.channel, r.celsius, r.timestamp) for r in readings] == [
        ("radio_food", 20.2, 5.0),
        ("radio_pit", 320.0, 5.0),
    ]


def test_other_devices_and_noise_give_nothing():
    assert parse_rtl433_line('{"model":"Acurite-Tower","temperature_C":3}', 0) == []
    assert parse_rtl433_line("rtl_433 version 25.12", 0) == []
    assert parse_rtl433_line("[1, 2]", 0) == []


def test_missing_or_non_numeric_field_is_skipped():
    line = '{"model":"Thermopro-TP12","temperature_1_C":"x","temperature_2_C":90.5}'
    assert [r.channel for r in parse_rtl433_line(line, 0)] == ["radio_pit"]


async def test_source_reads_lines_from_child_process():
    script = f"print({TP12!r}, flush=True); print('noise', flush=True)"
    source = RadioProbeSource()
    source.argv = [sys.executable, "-c", script]
    stream = source.readings()
    first = await anext(stream)
    second = await anext(stream)
    await stream.aclose()
    assert (first.channel, second.channel) == ("radio_food", "radio_pit")


async def test_missing_binary_is_reported_not_raised():
    import asyncio

    source = RadioProbeSource("no-such-rtl-433")
    task = asyncio.create_task(anext(source.readings()))
    await asyncio.sleep(0.2)
    task.cancel()
    assert "cannot start" in source.status


def _frame(field_id, payload, valid=True):
    from chefstemp_ble.protocol import DeviceMessage

    return DeviceMessage(field_id, payload, valid)


def test_ble_temperature_frame_becomes_ble_food_reading():
    reading = reading_from_message(_frame(0x71, (95).to_bytes(2, "big")), now=3.0)
    assert (reading.channel, reading.celsius, reading.timestamp) == ("ble_food", 95.0, 3.0)


def test_ble_battery_and_bad_checksum_frames_are_ignored():
    assert reading_from_message(_frame(0x10, bytes([80])), 0) is None
    assert reading_from_message(_frame(0x71, (95).to_bytes(2, "big"), valid=False), 0) is None


async def test_ble_source_yields_readings_then_reconnects_after_drop(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager

    monkeypatch.setattr("cooktemp_tui.sources.RETRY_MIN_SECONDS", 0.01)
    sessions = []

    @asynccontextmanager
    async def opener(on_message):
        lost = asyncio.Event()
        sessions.append(lost)
        on_message(_frame(0x71, (60 + len(sessions)).to_bytes(2, "big")))
        lost.set() if len(sessions) == 1 else None
        yield lost

    source = BleBaseSource(opener)
    stream = source.readings()
    first = await asyncio.wait_for(anext(stream), 2)
    second = await asyncio.wait_for(anext(stream), 2)
    await stream.aclose()
    assert (first.celsius, second.celsius) == (61.0, 62.0)


async def test_ble_source_reports_connect_failure():
    import asyncio
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def opener(on_message):
        raise RuntimeError("close the ChefsTemp app")
        yield

    source = BleBaseSource(opener)
    task = asyncio.create_task(anext(source.readings()))
    await asyncio.sleep(0.2)
    task.cancel()
    assert "close the ChefsTemp app" in source.status


async def test_merged_source_interleaves_sources():
    class One:
        def __init__(self, channel):
            self.channel = channel

        async def readings(self):
            yield Reading(self.channel, 1.0, 0.0)

    stream = MergedSource(One("ble_food"), One("radio_pit")).readings()
    got = {(await anext(stream)).channel, (await anext(stream)).channel}
    await stream.aclose()
    assert got == {"ble_food", "radio_pit"}


async def test_rtl433_startup_hint_is_not_shown_as_an_error():
    import asyncio

    script = (
        "import sys, time;"
        "print('Use \"-F log\" if you want any messages, warnings, and errors', file=sys.stderr, flush=True);"
        "time.sleep(1)"
    )
    source = RadioProbeSource()
    source.argv = [sys.executable, "-c", script]
    task = asyncio.create_task(anext(source.readings()))
    await asyncio.sleep(0.5)
    task.cancel()
    assert source.status == "listening on 433.92 MHz"
