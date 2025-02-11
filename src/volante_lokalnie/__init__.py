# this_file: src/volante_lokalnie/__init__.py

"""Volante Lokalnie package for managing offers on the platform.

This package provides tools for managing offers on the Volante Lokalnie platform,
including fetching, reading, and updating offers through a command-line interface.
"""

from .volante_lokalnie import VolanteCLI

__all__ = ["VolanteCLI"]
