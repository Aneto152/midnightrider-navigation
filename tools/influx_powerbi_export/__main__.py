"""
Module entry point: python3 -m tools.influx_powerbi_export
"""
import sys
from . import main

if __name__ == "__main__":
    sys.exit(main.main())
