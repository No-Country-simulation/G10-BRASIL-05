#!/usr/bin/env python3
"""Controla a stack Docker local de teste sem expor a chave OCI na imagem."""

import argparse
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.local-test.yml"
BACKEND_ENV = ROOT / "backend" / ".env"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "down", "ps", "logs"))
    args = parser.parse_args()

    values = dotenv_values(BACKEND_ENV)
    key_path = Path(values.get("OCI_KEY_FILE") or "").expanduser()
    if args.action == "up" and not key_path.is_file():
        parser.error("OCI_KEY_FILE do backend/.env está ausente ou não existe.")

    env = os.environ.copy()
    if key_path:
        env["OCI_KEY_FILE_HOST"] = str(key_path.resolve())

    command = [
        "docker", "compose",
        "--project-name", "mediflow-local-test",
        "--file", str(COMPOSE_FILE),
    ]
    if args.action == "up":
        command += ["up", "--detach", "--build"]
    elif args.action == "down":
        command += ["down"]
    elif args.action == "ps":
        command += ["ps"]
    else:
        command += ["logs", "--follow", "backend"]

    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
