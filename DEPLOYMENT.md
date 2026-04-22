# ObserverAI Deployment

ObserverAI Magnet Engine is structured as a monorepo with two deployable apps:

- Backend: FastAPI app at the repository root, with application code in `app/`.
- Frontend: Next.js app in `frontend/`.

No `vercel.json` is required. Vercel should use the `frontend` directory as the project root and keep the default Next.js build/output behavior.

## Frontend on Vercel

Use these Vercel project settings:

- Root Directory: `frontend`
- Framework Preset: `Next.js`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: leave blank/default
- Development Command: leave default or use `npm run dev`

Required frontend environment variables:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-backend.onrender.com
```

Local frontend commands:

```powershell
cd frontend
npm install
npm run typecheck
npm run build
npm run dev
```

## Backend on Render

Use these Render Web Service settings:

- Root Directory: leave blank / repository root
- Runtime: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Recommended Render environment variables:

```env
APP_ENV=production
DEBUG=false
PYTHON_VERSION=3.11.9
DATABASE_URL=sqlite:///./observerai.db
FRONTEND_BASE_URL=https://your-vercel-app.vercel.app
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
AUTH_JWT_SECRET=replace-with-a-long-random-secret
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
OPERATOR_EMAIL=operator@example.com
OPERATOR_PASSWORD=replace-with-a-strong-password
OPERATOR_ROLE=admin
STRIPE_SECRET_KEY=sk_live_or_test_key
TELEGRAM_ALERTS_ENABLED=false
```

If Telegram alerts are enabled, also set:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

The live MT5 runner is intentionally separate from the Render backend. Use `requirements-runner-py313.txt` and `.env.runner` for the Windows/MetaTrader runner environment.
