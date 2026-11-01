import pytest

from cooktemp_tui.model import (
    LIVE,
    NO_SIGNAL,
    STALE_SECONDS,
    UNPLUGGED,
    ChannelState,
    Reading,
    c_to_f,
    eta_seconds,
    f_to_c,
    format_eta,
    format_temp,
    is_unplugged,
    temp_color,
)


def test_unit_conversion_round_trips():
    assert c_to_f(100) == pytest.approx(212)
    assert f_to_c(203) == pytest.approx(95)
    assert f_to_c(c_to_f(57.3)) == pytest.approx(57.3)


def test_format_temp_uses_unit():
    assert format_temp(95, "F") == "203°F"
    assert format_temp(95, "C") == "95°C"


def test_placeholder_reading_is_unplugged():
    assert is_unplugged(320.0)
    assert not is_unplugged(107.0)


def test_color_moves_toward_red_near_target():
    assert temp_color(20, 95) == "dodger_blue1"
    assert temp_color(90, 95) == "yellow"
    assert temp_color(96, 95) == "red"


def rising(per_second, count=10, step=10.0, start=20.0):
    return [(i * step, start + per_second * i * step) for i in range(count)]


def test_eta_for_steady_rise():
    samples = rising(0.01)  # 0.01 C per second
    last_c = samples[-1][1]
    assert eta_seconds(samples, last_c + 1.0) == pytest.approx(100.0)


def test_eta_none_without_target_or_rise():
    assert eta_seconds(rising(0.01), None) is None
    assert eta_seconds(rising(0.0), 95) is None
    assert eta_seconds(rising(0.01)[:2], 95) is None


def test_eta_zero_when_target_reached():
    assert eta_seconds(rising(0.01), 10) == 0.0


def test_format_eta():
    assert format_eta(None) == "--"
    assert format_eta(30) == "<1 min"
    assert format_eta(18 * 60) == "~18 min"
    assert format_eta(65 * 60) == "~1 h 05 min"


def test_channel_state_transitions():
    state = ChannelState()
    assert state.state(now=0) == NO_SIGNAL

    state.add(Reading("ble_food", 60.0, 0.0), arrived=100.0)
    assert state.state(now=100.0) == LIVE
    assert state.state(now=100.0 + STALE_SECONDS + 1) == NO_SIGNAL

    state.add(Reading("radio_pit", 320.0, 1.0), arrived=200.0)
    assert state.state(now=200.0) == UNPLUGGED


def test_unplugged_reading_stays_out_of_history():
    state = ChannelState()
    state.add(Reading("radio_pit", 320.0, 0.0), arrived=0.0)
    assert not state.history
