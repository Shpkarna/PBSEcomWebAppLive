#!/usr/bin/env python3
"""Phase 5 setup utility for one-time database engine selection.

This command lets a fresh install choose the database engine at setup time,
persists the selection to backend/.env, and prints prerequisite diagnostics.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List


ENGINE_CHOICES = ("mongodb", "mysql", "sqlserver")
REQUIRED_ENV_BY_ENGINE = {
    "mongodb": ["MONGODB_URL"],
    "mysql": [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_DATABASE",
    ],
    "sqlserver": [
        "MSSQL_SERVER",
        "MSSQL_DATABASE",
        "MSSQL_DRIVER",
    ],
}
NOT_IMPLEMENTED_BY_ENGINE: dict[str, str] = {}
BOOTABLE_ENGINES = tuple(
    engine for engine in ENGINE_CHOICES if engine not in NOT_IMPLEMENTED_BY_ENGINE
)


def _default_env_file() -> Path:
    return Path(__file__).resolve().parent / ".env"


def bootable_engine_choices() -> tuple[str, ...]:
    """Return engines that can boot in the current build."""
    return BOOTABLE_ENGINES


def _selection_block_reason(engine: str) -> str | None:
    phase = NOT_IMPLEMENTED_BY_ENGINE.get(engine)
    if not phase:
        return None
    return (
        f"Engine '{engine}' cannot be selected in this build because its runtime driver is scheduled for {phase}. "
        "Keep DB_ENGINE set to 'mongodb' until that phase is complete."
    )


def _validate_persistable_engine(engine: str) -> None:
    if engine not in ENGINE_CHOICES:
        raise RuntimeError(
            f"Unsupported engine '{engine}'. Supported values: {', '.join(ENGINE_CHOICES)}."
        )

    blocker = _selection_block_reason(engine)
    if blocker:
        raise RuntimeError(blocker)


def read_env_file(env_file: Path) -> Dict[str, str]:
    """Read simple KEY=VALUE pairs from an env file."""
    if not env_file.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def upsert_env_key(env_file: Path, key: str, value: str) -> None:
    """Insert or replace a KEY=VALUE entry in an env file."""
    env_file.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    replaced = False
    output: List[str] = []

    for line in lines:
        if not line.lstrip().startswith("#") and pattern.match(line):
            output.append(f"{key}={value}")
            replaced = True
        else:
            output.append(line)

    if not replaced:
        output.append(f"{key}={value}")

    env_file.write_text("\n".join(output) + "\n", encoding="utf-8")


def persist_db_engine_selection(engine: str, env_file: Path, force: bool = False) -> str:
    """Persist DB_ENGINE to env file.

    Returns one of:
    - "created" when DB_ENGINE did not exist and was written
    - "updated" when force=True and DB_ENGINE changed
    - "unchanged" when the same value was already present
    """
    _validate_persistable_engine(engine)

    values = read_env_file(env_file)
    current = values.get("DB_ENGINE", "").strip().lower()

    if current:
        if current == engine:
            return "unchanged"
        if not force:
            raise RuntimeError(
                "DB_ENGINE is already set to "
                f"'{current}'. Use --force to change it to '{engine}'."
            )
        upsert_env_key(env_file, "DB_ENGINE", engine)
        return "updated"

    upsert_env_key(env_file, "DB_ENGINE", engine)
    return "created"


def _effective_env_values(env_file: Path) -> Dict[str, str]:
    values = read_env_file(env_file)
    for key, value in os.environ.items():
        if value is not None:
            values[key] = value
    return values


def prerequisite_diagnostics(engine: str, env_file: Path) -> List[str]:
    """Return diagnostics about missing engine prerequisites."""
    diagnostics: List[str] = []
    required = REQUIRED_ENV_BY_ENGINE.get(engine, [])
    effective = _effective_env_values(env_file)
    blocker = _selection_block_reason(engine)

    if blocker:
        diagnostics.append(blocker)

    missing = [key for key in required if not str(effective.get(key, "")).strip()]
    if missing:
        diagnostics.append(
            (
                "Preparation prerequisites missing for this future engine: "
                if blocker
                else "Missing prerequisite environment variables: "
            )
            + ", ".join(missing)
        )
    else:
        diagnostics.append(
            "All prerequisite environment variables are present for this future engine."
            if blocker
            else "All required environment variables are present."
        )

    return diagnostics


def _prompt_engine_selection() -> str:
    available = bootable_engine_choices()
    if not available:
        raise RuntimeError("No bootable database engines are available in this build.")

    print("Select database engine for this install:")
    mapping = {}
    for index, engine in enumerate(available, start=1):
        print(f"  {index}) {engine}")
        mapping[str(index)] = engine

    if NOT_IMPLEMENTED_BY_ENGINE:
        print("Planned but not selectable in this build:")
        for engine, phase in NOT_IMPLEMENTED_BY_ENGINE.items():
            print(f"  - {engine} ({phase})")

    while True:
        choice = input(f"Enter choice (1-{len(mapping)}): ").strip()
        if choice in mapping:
            return mapping[choice]
        print(f"Invalid choice. Please enter 1-{len(mapping)}.")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5 setup: choose and persist a bootable database engine selection.",
    )
    parser.add_argument(
        "--engine",
        choices=ENGINE_CHOICES,
        help="Engine to persist (mongodb, mysql, sqlserver).",
    )
    parser.add_argument(
        "--env-file",
        default=str(_default_env_file()),
        help="Path to environment file (default: backend/.env).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow changing DB_ENGINE if already set.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail if --engine is not provided instead of prompting.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    env_file = Path(args.env_file).resolve()

    selected_engine = args.engine
    if not selected_engine:
        current_engine = read_env_file(env_file).get("DB_ENGINE", "").strip().lower()
        if current_engine and not args.force:
            print(f"DB_ENGINE is already set to '{current_engine}' in {env_file}.")
            for line in prerequisite_diagnostics(current_engine, env_file):
                print(f"- {line}")
            if current_engine not in bootable_engine_choices():
                print("Use --force --engine mongodb to restore a bootable configuration.")
                return 2
            print("Use --force with --engine to change it.")
            return 0

        if args.non_interactive:
            print("--non-interactive requires --engine.")
            return 2
        selected_engine = _prompt_engine_selection()

    try:
        result = persist_db_engine_selection(selected_engine, env_file, force=args.force)
    except RuntimeError as error:
        print(f"Error: {error}")
        for line in prerequisite_diagnostics(selected_engine, env_file):
            if line != str(error):
                print(f"- {line}")
        return 2

    if result == "created":
        print(f"DB_ENGINE set to '{selected_engine}' in {env_file}.")
    elif result == "updated":
        print(f"DB_ENGINE updated to '{selected_engine}' in {env_file}.")
    else:
        print(f"DB_ENGINE already set to '{selected_engine}' in {env_file}.")

    for line in prerequisite_diagnostics(selected_engine, env_file):
        print(f"- {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
