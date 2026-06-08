from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def closed_loop_root(runtime_root: str | None = None) -> Path:
    base = PROJECT_ROOT / runtime_root if runtime_root else PROJECT_ROOT
    return base / "data" / "closed_loop"


def latest_watch_trade_date(runtime_root: str | None = None) -> str:
    root = closed_loop_root(runtime_root)
    if not root.exists():
        raise SystemExit(f"closed loop root not found: {root}")

    dates = sorted(path.name for path in root.iterdir() if path.is_dir() and (path / "watch.json").exists())
    if not dates:
        raise SystemExit(f"no watch.json found under: {root}")
    return dates[-1]


def script_path(name: str) -> Path:
    return PROJECT_ROOT / "scripts" / name


def build_command(task: str, time_label: str | None = None, runtime_root: str | None = None) -> list[str]:
    command = [sys.executable]

    if task == "morning-watch":
        command.append(str(script_path("morning_watch_925.py")))
    elif task == "snapshot":
        if not time_label:
            raise SystemExit("--time-label is required for snapshot")
        command.extend(
            [
                str(script_path("capture_intraday_snapshot.py")),
                "--trade-date",
                latest_watch_trade_date(runtime_root),
                "--time-label",
                time_label,
            ]
        )
    elif task == "daily":
        command.extend(
            [
                str(script_path("build_closed_loop_daily.py")),
                "--trade-date",
                latest_watch_trade_date(runtime_root),
            ]
        )
    elif task == "weekly":
        command.extend(
            [
                str(script_path("build_closed_loop_weekly.py")),
                "--end-date",
                latest_watch_trade_date(runtime_root),
            ]
        )
    else:
        raise SystemExit(f"unsupported task: {task}")

    if runtime_root:
        command.extend(["--runtime-root", runtime_root])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one closed-loop automation task.")
    parser.add_argument("task", choices=["morning-watch", "snapshot", "daily", "weekly"])
    parser.add_argument("--time-label", choices=["09:35", "10:00", "10:30", "14:30"])
    parser.add_argument("--runtime-root", default=None, help="Fallback output root for restricted environments.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without executing it.")
    args = parser.parse_args()

    command = build_command(args.task, time_label=args.time_label, runtime_root=args.runtime_root)
    print(" ".join(command))
    if args.dry_run:
        return

    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
