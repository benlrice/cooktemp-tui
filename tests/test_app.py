import pytest

from cooktemp_tui.app import CookApp, render_readout
from cooktemp_tui.model import ChannelState, Reading, f_to_c
from cooktemp_tui.sources import DemoSource, demo_celsius


class ScriptedSource:
    """Yields a fixed list of readings, then stops."""

    def __init__(self, readings):
        self._readings = readings

    async def readings(self):
        for reading in self._readings:
            yield reading


def test_demo_curves_rise_and_stay_below_unplugged():
    for channel in ("ble_food", "radio_food", "radio_pit"):
        assert demo_celsius(channel, 0) < demo_celsius(channel, 3600) < 200


def test_demo_curve_rejects_unknown_channel():
    with pytest.raises(KeyError):
        demo_celsius("nope", 0)


def test_readout_shows_value_and_target():
    state = ChannelState()
    state.add(Reading("ble_food", 95.0, 0.0), arrived=10.0)
    state.target_c = f_to_c(225)
    plain = render_readout(state, now=10.0, unit="F").plain
    assert "203°F" in plain
    assert "target 225°F" in plain


def test_readout_for_missing_and_unplugged():
    state = ChannelState()
    assert render_readout(state, now=0, unit="F").plain == "no signal"
    state.add(Reading("radio_pit", 320.0, 0.0), arrived=0.0)
    assert render_readout(state, now=0, unit="F").plain == "unplugged"


async def test_app_takes_readings_and_keys():
    source = ScriptedSource(
        [
            Reading("ble_food", 60.0, 0.0),
            Reading("radio_pit", 320.0, 0.0),
        ]
    )
    app = CookApp(source)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.channels["ble_food"].celsius == 60.0
        assert app.channels["radio_pit"].celsius == 320.0

        await pilot.press("u")
        assert app.unit == "C"

        await pilot.press("up")
        assert app.channels["ble_food"].target_c == pytest.approx(f_to_c(203))
        await pilot.press("up")
        assert app.channels["ble_food"].target_c == pytest.approx(f_to_c(208))
        await pilot.press("c")
        assert app.channels["ble_food"].target_c is None


async def test_app_runs_on_demo_source():
    app = CookApp(DemoSource(interval=0.05, speed=600.0))
    async with app.run_test() as pilot:
        await pilot.pause(0.3)
        assert app.channels["ble_food"].celsius is not None
        assert app.channels["radio_pit"].history
