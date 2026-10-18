import sys

from mingo_assistant.app.main import main


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--portable-self-test":
        from mingo_assistant.app.portable_self_test import run_portable_self_test

        raise SystemExit(run_portable_self_test(sys.argv[2]))
    main()
