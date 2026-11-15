"""Entrypoint for `python -m neural_canvas`."""

from __future__ import annotations

import sys

from neural_canvas.cli import main

if __name__ == "__main__":
    sys.exit(main())
