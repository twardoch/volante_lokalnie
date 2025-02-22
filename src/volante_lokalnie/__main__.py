#!/usr/bin/env python3
# this_file: src/volante_lokalnie/__main__.py

"""Main entry point for Volante Lokalnie."""

import sys

import fire

from volante_lokalnie.tui import VolanteTUI
from volante_lokalnie.volante_lokalnie import VolanteCLI


def main() -> None:
    """Run the application in either CLI or TUI mode.

    If command line arguments are provided, run in CLI mode.
    Otherwise, launch the TUI interface.
    """
    if len(sys.argv) > 1:
        # If arguments are present, use the Fire CLI
        fire.Fire(VolanteCLI)
    else:
        # If no arguments, run the Textual TUI
        app = VolanteTUI()
        app.run()


if __name__ == "__main__":
    main()
