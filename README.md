# cooktemp-tui

A colorful terminal dashboard for cook temperatures. It shows two types of thermometer on one screen:

- a Bluetooth Low Energy (BLE) thermometer base. The program reads it with [chefstemp-ble](https://github.com/benlrice/chefstemp-ble).
- a 433 MHz radio probe. The program reads it with `rtl_433` and an RTL-SDR dongle.

This program runs in Linux, including WSL.

## Status

The program reads both thermometers. It writes every reading to a file, and it can play a past cook again.

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
- `--replay FILE` plays a cook file again with the original timing. Use `--speed N` to make it faster.
- `--log-file FILE` writes the readings to FILE. The default file name is `cook-DATE-TIME.jsonl` in the current folder.
- `--no-log` does not write a cook file.
- `--demo` shows simulated readings. No hardware is necessary.
- `--speed N` makes the demo or the replay run N times faster than real time. The default is 60 for the demo and 1 for the replay.

## Important: one BLE connection only

The BLE base accepts one connection at a time. Close the thermometer app on your phone before you start this program. If the phone app is connected, this program cannot connect.

## Cook files

A cook file has one JSON line for each reading. Each line has the seconds since the start, the clock time, the channel, and the temperature in °C. The file also holds the `unplugged` placeholder readings. The `.gitignore` file excludes `cook-*.jsonl` files.

## How it works

- The program starts `rtl_433` as a child process and keeps only `Thermopro-TP12` messages. If `rtl_433` stops, the program starts it again.
- The program connects to the BLE base and reads the temperature. If the connection is lost, the program connects again.
- Each retry waits longer than the last retry, up to 30 seconds.

## Plan

- Show the battery level of the BLE base.

## Develop

```
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/pytest
```
