"""Command line entry point: `python -m cooktemp_tui`."""

import argparse
import sys
from pathlib import Path

from cooktemp_tui.app import CookApp
from cooktemp_tui.recording import LoggingSource, ReplaySource, default_log_path
from cooktemp_tui.sources import (
    BleBaseSource,
    DemoSource,
    MergedSource,
    RadioProbeSource,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cooktemp-tui", description=__doc__)
    parser.add_argument("--no-ble", action="store_true", help="skip the Bluetooth base")
    parser.add_argument("--replay", type=Path, metavar="FILE", help="play back a cook file")
    parser.add_argument("--log-file", type=Path, metavar="FILE", help="write readings here")
    parser.add_argument("--no-log", action="store_true", help="do not write a cook file")
    parser.add_argument("--demo", action="store_true", help="run on simulated readings")
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="demo and replay: how many cook seconds pass per real second (demo 60, replay 1)",
    )
    args = parser.parse_args(argv)
    if args.replay:
        if not args.replay.is_file():
            print(f"No such file: {args.replay}", file=sys.stderr)
            return 2
        source = ReplaySource(args.replay, speed=args.speed or 1.0)
        CookApp(source, subtitle=f"replay {args.replay.name}").run()
    elif args.demo:
        CookApp(DemoSource(speed=args.speed or 60.0), subtitle="demo").run()
    else:
        sources = [RadioProbeSource()]
        if not args.no_ble:
            sources.append(BleBaseSource())
        source = MergedSource(*sources)
        subtitle = "live"
        if not args.no_log:
            path = args.log_file or default_log_path()
            source = LoggingSource(source, path)
            subtitle = f"live, logging to {path}"
        CookApp(source, subtitle=subtitle).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
