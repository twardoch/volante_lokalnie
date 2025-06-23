#!/usr/bin/env python3
# this_file: src/volante_lokalnie/__main__.py

"""Main entry point for the volante_lokalnie package.

This module provides the main entry point when running the package as a module
using `python -m volante_lokalnie`. It uses the Fire CLI framework for automatic
command-line interface generation and Rich for beautiful terminal output.

Example:
    python -m volante_lokalnie --help
"""

from typing import NoReturn

import fire
from rich.console import Console
from rich.traceback import install

# Install rich traceback handler for better error reporting
install(show_locals=True)

# Initialize rich console for pretty output
console = Console()


def main() -> NoReturn:
    """Main entry point for the CLI application.

    This function uses Google's Fire library to automatically generate a CLI
    from the package's main functionality. It provides a clean interface to
    all the package's features with automatic help generation.
    """
    try:
        # Import the main functionality
        from .volante_lokalnie import VolanteCLI

        # Use Fire to create the CLI
        fire.Fire(VolanteCLI)
    except Exception as e:
        console.print_exception()
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
