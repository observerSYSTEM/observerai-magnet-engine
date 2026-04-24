# MT5 Runner Setup

This project supports a separate MetaTrader 5 runner environment so the live MT5 dependency stack does not disturb the FastAPI backend environment.

## Strategy

- Keep the backend in its existing environment.
- Create a dedicated Python 3.13 virtual environment just for the MT5 runner.
- Use `.env.runner` for MT5 and runner settings.
- Run the backend and the runner as separate processes.

## Files

- Runner launcher: `scripts/run_mt5_runner.py`
- Runner dependencies: `requirements-runner-py313.txt`
- Runner env template: `.env.runner.example`

## Setup Commands

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv-runner313
.\.venv-runner313\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-runner-py313.txt
Copy-Item .env.runner.example .env.runner
```

## Configure `.env.runner`

Set the runner-only environment values in `.env.runner`:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
API_BASE_URL=https://observerai-magnet-engine.onrender.com
RUNNER_INTERVAL_SECONDS=60
DEFAULT_SYMBOL=XAUUSD
```

Notes:

- `API_BASE_URL` should point to the already running FastAPI backend.
- `RUNNER_INTERVAL_SECONDS` controls how often the MT5 runner gathers data and posts to `/oracle/evaluate`.
- `TELEGRAM_*` settings remain part of the backend environment and do not need to be duplicated here unless you also want them in the runner shell.

## Run Backend

Use your existing backend environment in a separate terminal:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Run Runner

In the Python 3.13 runner environment:

```powershell
.\.venv-runner313\Scripts\Activate.ps1
python .\scripts\run_mt5_runner.py
```

The runner loads `.env.runner` automatically before importing shared app settings.

## Optional Custom Runner Env File

To use a different runner env file:

```powershell
$env:RUNNER_ENV_FILE="F:\observerai-magnet-engine\.env.runner"
python .\scripts\run_mt5_runner.py
```

## What The Runner Does

Each cycle it:

- connects to MetaTrader 5
- gathers M1 candles for the current trading day
- gathers M15 candles
- gathers daily candles for levels and ADR
- computes current price, previous M15 close, and ATR(M1)
- posts the payload to `POST /oracle/evaluate`
- logs heartbeat, payload generation, response summary, and retryable failures
