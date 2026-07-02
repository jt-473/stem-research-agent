"""Entry point so you can run `python main.py ...` from the project root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Paper titles and model output contain unicode; some Windows consoles
# default to a legacy codepage and would crash on print. Force UTF-8 and
# replace anything unprintable instead of dying.
for stream in (sys.stdout, sys.stderr):
    if stream and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from agent.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
