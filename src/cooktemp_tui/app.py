"""The Textual screen: one panel per gauge, with a graph under each."""

import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Sparkline, Static

from cooktemp_tui.model import (
    CHANNELS,
    DEFAULT_TARGET_F,
    LIVE,
    NO_SIGNAL,
    ChannelState,
    Reading,
    c_to_f,
    f_to_c,
    format_eta,
    format_temp,
    temp_color,
)
from cooktemp_tui.sources import Source

BAR_WIDTH = 28
TARGET_STEP_F = 5


def render_readout(state: ChannelState, now: float, unit: str) -> Text:
    """The text inside one gauge panel."""
    text = Text()
    status = state.state(now)
    if status == NO_SIGNAL:
        if state.arrived is None:
            text.append("no signal", style="dim")
        else:
            text.append(f"no signal ({int(now - state.arrived)} s ago)", style="dim")
        return text
    if status != LIVE:
        text.append(status, style="dim")
        return text
    celsius = state.celsius
    color = temp_color(celsius, state.target_c)
    text.append(format_temp(celsius, unit), style=f"bold {color}")
    reference = state.target_c if state.target_c is not None else 150.0
    filled = round(min(celsius / reference, 1.0) * BAR_WIDTH)
    text.append("  ")
    text.append("█" * filled, style=color)
    text.append("░" * (BAR_WIDTH - filled), style="grey37")
    text.append("\n")
    if state.target_c is None:
        text.append("target: none (press ↑ to set)", style="dim")
    else:
        target = format_temp(state.target_c, unit)
        text.append(f"target {target}   ETA {format_eta(state.eta())}")
    return text


class GaugePanel(Vertical, can_focus=True):
    """One thermometer channel: readout on top, graph below."""

    def __init__(self, channel: str) -> None:
        super().__init__(id=channel)
        self.channel = channel
        self.border_title = CHANNELS[channel]

    def compose(self) -> ComposeResult:
        yield Static(classes="readout")
        yield Sparkline([], classes="graph")


class CookApp(App):
    TITLE = "cooktemp-tui"

    CSS = """
    GaugePanel { border: round $primary; height: 1fr; padding: 0 1; }
    GaugePanel:focus { border: round $accent; }
    .readout { height: 3; }
    .graph { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("u", "toggle_units", "°F/°C"),
        ("up", "raise_target", "Target +5°F"),
        ("down", "lower_target", "Target -5°F"),
        ("c", "clear_target", "Clear target"),
    ]

    def __init__(self, source: Source, subtitle: str = "") -> None:
        super().__init__()
        self.source = source
        self.sub_title = subtitle
        self.unit = "F"
        self.channels = {channel: ChannelState() for channel in CHANNELS}

    def compose(self) -> ComposeResult:
        yield Header()
        for channel in CHANNELS:
            yield GaugePanel(channel)
        yield Footer()

    def on_mount(self) -> None:
        self.query(GaugePanel).first().focus()
        self.set_interval(1.0, self.redraw_all)
        self.run_worker(self.consume(), exclusive=True)

    async def consume(self) -> None:
        async for reading in self.source.readings():
            self.handle_reading(reading)

    def handle_reading(self, reading: Reading) -> None:
        self.channels[reading.channel].add(reading, time.monotonic())
        self.redraw(reading.channel)

    def redraw(self, channel: str) -> None:
        state = self.channels[channel]
        panel = self.query_one(f"#{channel}", GaugePanel)
        readout = render_readout(state, time.monotonic(), self.unit)
        panel.query_one(".readout", Static).update(readout)
        panel.query_one(".graph", Sparkline).data = [c for _, c in state.history]

    def redraw_all(self) -> None:
        for channel in CHANNELS:
            self.redraw(channel)

    def action_toggle_units(self) -> None:
        self.unit = "C" if self.unit == "F" else "F"
        self.redraw_all()

    def action_raise_target(self) -> None:
        self.nudge_target(TARGET_STEP_F)

    def action_lower_target(self) -> None:
        self.nudge_target(-TARGET_STEP_F)

    def action_clear_target(self) -> None:
        panel = self.focused
        if isinstance(panel, GaugePanel):
            self.channels[panel.channel].target_c = None
            self.redraw(panel.channel)

    def nudge_target(self, delta_f: int) -> None:
        panel = self.focused
        if not isinstance(panel, GaugePanel):
            return
        state = self.channels[panel.channel]
        if state.target_c is None:
            state.target_c = f_to_c(DEFAULT_TARGET_F[panel.channel])
        else:
            state.target_c = f_to_c(round(c_to_f(state.target_c)) + delta_f)
        self.redraw(panel.channel)
