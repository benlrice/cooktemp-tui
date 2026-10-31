import sys

from cooktemp_tui.sources import RadioProbeSource, parse_rtl433_line

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
