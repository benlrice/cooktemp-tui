import json

from cooktemp_tui.model import Reading
from cooktemp_tui.recording import LoggingSource, ReplaySource, read_cook


class Scripted:
    def __init__(self, readings):
        self._readings = readings

    async def readings(self):
        for reading in self._readings:
            yield reading


async def test_logging_writes_every_reading_including_unplugged(tmp_path):
    path = tmp_path / "cook.jsonl"
    source = LoggingSource(
        Scripted([Reading("ble_food", 52.0, 0.0), Reading("radio_pit", 320.0, 0.0)]), path
    )
    got = [reading async for reading in source.readings()]
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(got) == 2
    assert [(r["channel"], r["celsius"]) for r in lines] == [
        ("ble_food", 52.0),
        ("radio_pit", 320.0),
    ]
    assert {"elapsed", "wall"} <= set(lines[0])


def test_read_cook_skips_bad_lines_and_sorts(tmp_path):
    path = tmp_path / "cook.jsonl"
    path.write_text(
        '{"elapsed": 5, "channel": "ble_food", "celsius": 60}\n'
        "not json\n"
        '{"elapsed": 1, "channel": "radio_food", "celsius": 20}\n'
        '{"elapsed": 2, "channel": "radio_food"}\n'
    )
    assert [(e, r.channel) for e, r in read_cook(path)] == [
        (1.0, "radio_food"),
        (5.0, "ble_food"),
    ]


async def test_replay_returns_logged_readings_then_stops(tmp_path):
    path = tmp_path / "cook.jsonl"
    path.write_text(
        '{"elapsed": 0.0, "channel": "ble_food", "celsius": 50}\n'
        '{"elapsed": 10.0, "channel": "ble_food", "celsius": 55}\n'
    )
    source = ReplaySource(path, speed=1000.0)
    assert [r.celsius async for r in source.readings()] == [50.0, 55.0]
