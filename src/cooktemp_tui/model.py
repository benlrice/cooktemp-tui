"""Temperature math and per-gauge state, with no screen code."""

from collections import deque
from dataclasses import dataclass, field

CHANNELS = {
    "ble_food": "BLE food",
    "radio_food": "Radio food",
    "radio_pit": "Radio pit",
}

DEFAULT_TARGET_F = {"ble_food": 203, "radio_food": 203, "radio_pit": 225}

# The radio probe reports about 320 C for a channel with no probe plugged in.
UNPLUGGED_C = 300.0
STALE_SECONDS = 60.0
ETA_WINDOW_SECONDS = 300.0
MIN_RISE_C_PER_SECOND = 0.0002
HISTORY_LENGTH = 600

LIVE = "live"
NO_SIGNAL = "no signal"
UNPLUGGED = "unplugged"


@dataclass(frozen=True)
class Reading:
    """One temperature from one channel. `timestamp` is in seconds."""

    channel: str
    celsius: float
    timestamp: float


def c_to_f(celsius: float) -> float:
    return celsius * 9 / 5 + 32


def f_to_c(fahrenheit: float) -> float:
    return (fahrenheit - 32) * 5 / 9


def is_unplugged(celsius: float) -> bool:
    return celsius >= UNPLUGGED_C


def format_temp(celsius: float, unit: str) -> str:
    if unit == "C":
        return f"{celsius:.0f}°C"
    return f"{c_to_f(celsius):.0f}°F"


def temp_color(celsius: float, target_c: float | None) -> str:
    """A color that moves from cold blue to hot red as the target nears."""
    reference = target_c if target_c is not None else 150.0
    ratio = celsius / reference
    if ratio < 0.4:
        return "dodger_blue1"
    if ratio < 0.7:
        return "cyan"
    if ratio < 0.9:
        return "green3"
    if ratio < 1.0:
        return "yellow"
    return "red"


def eta_seconds(samples: list[tuple[float, float]], target_c: float | None) -> float | None:
    """Seconds until the target, from a straight line through recent samples.

    Returns None when there is no target, too few samples, or no rise.
    """
    if target_c is None or not samples:
        return None
    last_time, last_c = samples[-1]
    if last_c >= target_c:
        return 0.0
    window = [(t, c) for t, c in samples if t >= last_time - ETA_WINDOW_SECONDS]
    if len(window) < 3:
        return None
    mean_t = sum(t for t, _ in window) / len(window)
    mean_c = sum(c for _, c in window) / len(window)
    spread = sum((t - mean_t) ** 2 for t, _ in window)
    if spread == 0:
        return None
    slope = sum((t - mean_t) * (c - mean_c) for t, c in window) / spread
    if slope < MIN_RISE_C_PER_SECOND:
        return None
    return (target_c - last_c) / slope


def format_eta(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    minutes = int(seconds // 60)
    if minutes < 1:
        return "<1 min"
    if minutes < 60:
        return f"~{minutes} min"
    return f"~{minutes // 60} h {minutes % 60:02d} min"


@dataclass
class ChannelState:
    """Everything the screen needs to draw one gauge."""

    history: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    celsius: float | None = None
    arrived: float | None = None
    target_c: float | None = None

    def add(self, reading: Reading, arrived: float) -> None:
        """Record a reading. `arrived` is local receive time, used for staleness."""
        self.celsius = reading.celsius
        self.arrived = arrived
        if not is_unplugged(reading.celsius):
            self.history.append((reading.timestamp, reading.celsius))

    def state(self, now: float) -> str:
        if self.arrived is None or self.celsius is None:
            return NO_SIGNAL
        if now - self.arrived > STALE_SECONDS:
            return NO_SIGNAL
        if is_unplugged(self.celsius):
            return UNPLUGGED
        return LIVE

    def eta(self) -> float | None:
        return eta_seconds(list(self.history), self.target_c)
