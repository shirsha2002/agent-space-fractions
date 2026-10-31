"""Source and frozen entry point. Worker mode is also bundled in the EXE."""
from pathlib import Path
import sys

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        if len(sys.argv) not in {5, 6} or (len(sys.argv) == 6 and sys.argv[5] != "--no-contract"):
            return 2
        from code_agent.worker import run
        return run(sys.argv[2], sys.argv[3], sys.argv[4], "--no-contract" not in sys.argv)
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        from code_agent.self_test import main as check
        return check(sys.argv[2:])
    from code_agent.ui import main as ui_main
    ui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
