"""Entry point of the packaged Gachashift.exe (also works from source: python Gachashift.py).

    Gachashift.exe                  opens the app
    Gachashift.exe run [options]    a run, with the same options as `python -m gachashift`
"""

import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from gachashift.__main__ import main as run_main
        run_main()
    else:
        from gachashift.ui.__main__ import main as app_main
        app_main()


if __name__ == "__main__":
    main()
