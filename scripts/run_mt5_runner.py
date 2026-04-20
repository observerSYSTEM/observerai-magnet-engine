from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_runner_env() -> None:
    """
    Load a dedicated runner environment file before shared settings are imported.

    This keeps the FastAPI backend environment separate from the MT5 runner.
    """

    default_env_file = REPO_ROOT / ".env.runner"
    env_file = Path(os.environ.get("RUNNER_ENV_FILE", default_env_file))
    if env_file.exists():
        load_dotenv(env_file, override=False)


_load_runner_env()

from app.services.mt5_runner import run_live_mt5_runner


if __name__ == "__main__":
    run_live_mt5_runner()
