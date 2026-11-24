"""Premium Bubble Shooter - entry point."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        from game.app import App
        App().run()
    except Exception:
        log = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "error_log.txt")
        try:
            with open(log, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except OSError:
            pass
        traceback.print_exc()
        input("The game crashed (see error_log.txt). Press Enter to close...")


if __name__ == "__main__":
    main()
