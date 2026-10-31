"""Command line entry point: `python -m cooktemp_tui`."""

import argparse
import sys

from cooktemp_tui.app import CookApp
from cooktemp_tui.sources import DemoSource, RadioProbeSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cooktemp-tui", description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run on simulated readings")
    parser.add_argument(
        "--speed",
        type=float,
        default=60.0,
        help="demo only: how many cook seconds pass per real second (default 60)",
    )
    args = parser.parse_args(argv)
    if args.demo:
        CookApp(DemoSource(speed=args.speed), subtitle="demo").run()
    else:
        CookApp(RadioProbeSource(), subtitle="radio probe").run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
