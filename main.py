"""Entry point so you can run `python main.py ...` from the project root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
