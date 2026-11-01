# cooktemp-tui

A colorful terminal dashboard for cook temperatures. It shows two types of thermometer on one screen:

- a Bluetooth Low Energy (BLE) thermometer base. The program reads it with [chefstemp-ble](https://github.com/benlrice/chefstemp-ble).
- a 433 MHz radio probe. The program reads it with `rtl_433` and an RTL-SDR dongle.

This program runs in Linux, including WSL.

## Status

Version 0.1.0. The program reads both thermometers. Logging and replay are not available yet.

## What you see

- Three gauges: BLE food, radio food, and radio pit. The color of a gauge changes as the temperature goes up.
- A graph for each gauge.
- A target temperature for each gauge, with an estimate of the time to the target.
- A gauge shows `no signal` when it has no new reading for 60 seconds.
- A gauge shows `unplugged` when the radio probe has no probe in its socket.

## Requirements

- Linux or WSL
- Python 3.10 or later
- For the radio probe: an RTL-SDR dongle and the `rtl_433` program (`sudo apt install rtl-433`)
- For the BLE base: a Bluetooth adapter that BlueZ can use (`sudo apt install bluez`)

WSL cannot use a USB device until you attach it. Use `usbipd` for this.

## Install

```
git clone https://github.com/benlrice/cooktemp-tui
cd cooktemp-tui
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Use

```
.venv/bin/python -m cooktemp_tui
```

| Key | Action |
| --- | --- |
| `u` | Change between °F and °C |
| `up` | Increase the target by 5 °F. The first press sets the default target. |
| `down` | Decrease the target by 5 °F |
| `c` | Clear the target |
| `q` | Quit |

Options:

- `--no-ble` does not use the BLE base.
- `--demo` shows simulated readings. No hardware is necessary.
- `--speed N` makes the demo run N times faster than real time. The default is 60.

## Important: one BLE connection only

The BLE base accepts one connection at a time. Close the thermometer app on your phone before you start this program. If the phone app is connected, this program cannot connect.

## How it works

- The program starts `rtl_433` as a child process and keeps only `Thermopro-TP12` messages. If `rtl_433` stops, the program starts it again.
- The program connects to the BLE base and reads the temperature. If the connection is lost, the program connects again.
- Each retry waits longer than the last retry, up to 30 seconds.

## Plan

- Write every reading to a file. Use `--replay <file>` to play a past cook again.
- Show the battery level of the BLE base.

## Develop

```
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/pytest
```
