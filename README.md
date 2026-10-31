# cooktemp-tui

A colorful terminal dashboard for cook temperatures. It shows two kinds of thermometer on one screen:

- a Bluetooth Low Energy (BLE) thermometer base, read with [chefstemp-ble](https://github.com/benlrice/chefstemp-ble)
- a 433 MHz radio probe, read with `rtl_433` and an RTL-SDR dongle

This project runs in Linux, including WSL.

## Status

Early work. Milestone 1 is `--demo` mode: the full screen, driven by simulated readings. No hardware is read yet.

## Plan

- Three color-shifting gauges: BLE food, radio food, radio pit.
- A scrolling graph of all gauges.
- A target temperature for each gauge, with a time-to-target estimate.
- °F by default. A key switches to °C.
- Every reading is logged to a file. `--replay <file>` plays a past cook back.
