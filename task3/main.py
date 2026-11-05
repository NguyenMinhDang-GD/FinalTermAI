import sys
from gui import KakuroGUI


def main():
    puzzle_arg = sys.argv[1] if len(sys.argv) > 1 else None
    app = KakuroGUI(initial_puzzle=puzzle_arg)
    app.run()


if __name__ == "__main__":
    main()
