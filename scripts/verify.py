"""Run the repository's repeatable local/CI quality gates."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, command: list[str], env: dict[str, str]) -> None:
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile, lint, type-check and test Min Assistant.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run compile/lint/type/diff gates without unit or integration tests.",
    )
    args = parser.parse_args()

    python = sys.executable
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONIOENCODING": "utf-8",
        "QT_QPA_PLATFORM": "offscreen",
    })
    with tempfile.TemporaryDirectory(prefix="mingo-verify-pycache-") as cache_dir:
        env["PYTHONPYCACHEPREFIX"] = cache_dir
        env["MYPY_CACHE_DIR"] = str(Path(cache_dir) / "mypy")
        env["RUFF_CACHE_DIR"] = str(Path(cache_dir) / "ruff")
        stages = [
            ("compile", [python, "-m", "compileall", "-q", "src", "tests"]),
            ("ruff", [python, "-m", "ruff", "check", "src", "tests"]),
            ("mypy", [python, "-m", "mypy"]),
        ]
        if not args.fast:
            stages.extend([
                ("unit", [python, "-m", "unittest", "discover", "-s", "tests/unit"]),
                (
                    "integration",
                    [python, "-m", "unittest", "discover", "-s", "tests/integration"],
                ),
            ])
        stages.append(("diff-check", ["git", "diff", "--check"]))
        try:
            for label, command in stages:
                _run(label, command, env)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"\nVerification failed: {exc}", file=sys.stderr)
            return 1

    print("\nAll requested verification gates passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
