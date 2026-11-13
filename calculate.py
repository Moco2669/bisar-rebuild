"""Start the local Calculate page: python calculate.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from bisar.app import main

if __name__ == "__main__":
    main()
