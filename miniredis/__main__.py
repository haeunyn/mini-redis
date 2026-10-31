"""python -m miniredis 로 실행하는 진입점."""

import sys

from .cli import run

if __name__ == "__main__":
    sys.exit(run())
