# ObserverAI Magnet Engine v1

A FastAPI backend scaffold for an M15 market intelligence engine focused on XAUUSD.

## What this scaffold includes
- FastAPI app bootstrap
- SQLAlchemy models for candles, market state, and signals
- Pydantic schemas
- Core engines: levels, anchor, ADR, events, magnets, confidence, alerts
- API routes for ingest, oracle evaluation, market map, and latest signals
- Telegram service stub
- Local SQLite default for easy startup
- Test skeletons

## Quick start
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open docs at `http://127.0.0.1:8000/docs`.

## MT5 Runner

The live MetaTrader 5 runner is intended to use a separate Python 3.13 environment so it does not disturb the FastAPI backend environment.

See [docs/mt5_runner_setup.md](docs/mt5_runner_setup.md) for:

- the dedicated runner dependency file
- `.env.runner` setup
- exact Python 3.13 virtualenv commands
- the runner launch command against `http://127.0.0.1:8000`
