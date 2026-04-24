import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import get_settings

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def signals_dashboard() -> HTMLResponse:
    symbols_json = json.dumps(get_settings().runner_symbols)
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ObserverAI Signals Dashboard</title>
  <style>
    :root {
      --bg: #f4f1eb;
      --panel: #ffffff;
      --panel-soft: #fbf8f3;
      --ink: #14181d;
      --muted: #69717c;
      --line: #d8d1c5;
      --accent: #8d7447;
      --buy: #1e6a46;
      --sell: #9a4033;
      --wait: #7f6c3c;
      --shadow: 0 18px 40px rgba(20, 24, 29, 0.06);
      --shadow-soft: 0 10px 24px rgba(20, 24, 29, 0.04);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }

    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 56px;
    }

    .masthead {
      display: grid;
      gap: 12px;
      margin-bottom: 20px;
    }

    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    h1, h2, h3 {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 600;
      letter-spacing: -0.02em;
    }

    h1 {
      font-size: clamp(28px, 4vw, 42px);
      line-height: 1.08;
    }

    h2 {
      font-size: 25px;
      line-height: 1.2;
    }

    h3 {
      font-size: 18px;
      line-height: 1.25;
    }

    .subhead {
      margin: 0;
      max-width: 860px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.7;
    }

    .topbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 20px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.82);
      box-shadow: var(--shadow-soft);
    }

    .topbar-group {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }

    button {
      min-height: 40px;
      padding: 0 16px;
      border: 0;
      border-radius: 999px;
      background: var(--ink);
      color: #f8f6f1;
      font: inherit;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 140ms ease, transform 140ms ease;
    }

    button:hover {
      opacity: 0.94;
      transform: translateY(-1px);
    }

    .status {
      color: var(--muted);
      font-size: 13px;
    }

    .timer {
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
    }

    .stack {
      display: grid;
      gap: 20px;
    }

    .section {
      display: grid;
      gap: 16px;
    }

    .section-head {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
    }

    .section-head span {
      color: var(--muted);
      font-size: 14px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .card-body {
      padding: 22px;
    }

    .accent-card {
      background: linear-gradient(180deg, rgba(250, 248, 244, 0.96), rgba(255, 255, 255, 1));
    }

    .headline {
      display: grid;
      gap: 10px;
    }

    .headline p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.65;
    }

    .badge-row,
    .tile-top,
    .liquidity-top {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--ink);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .buy { color: var(--buy); }
    .sell { color: var(--sell); }
    .wait { color: var(--wait); }
    .tradeable-yes { color: var(--buy); }
    .tradeable-no { color: var(--wait); }

    .grid-3,
    .grid-2,
    .mini-grid,
    .liquidity-list {
      display: grid;
      gap: 12px;
    }

    .grid-3 {
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }

    .grid-2 {
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    }

    .mini-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .metric,
    .mini-row,
    .liquidity-item {
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.9);
    }

    .metric-label,
    .mini-row span:first-child,
    .liquidity-kicker {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .metric-value,
    .mini-row span:last-child,
    .liquidity-main {
      display: block;
      font-size: 18px;
      line-height: 1.35;
    }

    .tile,
    .liquidity-card {
      display: grid;
      gap: 14px;
    }

    .tile-reason,
    .liquidity-reason {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
      white-space: normal;
      overflow-wrap: anywhere;
    }

    .liquidity-meta {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .empty {
      padding: 28px 20px;
      text-align: center;
      color: var(--muted);
    }

    .empty strong {
      display: block;
      margin-bottom: 8px;
      color: var(--ink);
      font-size: 20px;
    }

    @media (max-width: 760px) {
      .shell {
        width: min(100%, calc(100% - 24px));
      }

      .card-body {
        padding: 18px;
      }

      .mini-grid,
      .liquidity-meta {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="masthead">
      <span class="eyebrow">ObserverAI Magnet Engine</span>
      <h1>Signals Dashboard</h1>
      <p class="subhead">
        Scalping EA context stays strict and fast around M1 and M15 execution, while the dashboard also surfaces H1 and H4 liquidity magnets for swing-aware monitoring across supported symbols.
      </p>
    </section>

    <section class="topbar">
      <div class="topbar-group">
        <button id="refresh-btn" type="button">Refresh</button>
      </div>
      <div class="topbar-group">
        <span id="m15-timer" class="timer">Next M15 close in: 15:00</span>
        <span id="status" class="status">Waiting for data...</span>
      </div>
    </section>

    <section class="stack">
      <article class="card accent-card">
        <div id="best-signal" class="card-body empty">
          <strong>Best Signal Now</strong>
          No strong signal available
        </div>
      </article>

      <section class="section">
        <div class="section-head">
          <h2>Scalping Signals</h2>
          <span>M1/M15 execution view</span>
        </div>
        <div id="symbol-grid" class="grid-3">
          <article class="card">
            <div class="card-body empty">
              <strong>Loading symbols...</strong>
              ObserverAI is preparing the latest scalping signal tiles.
            </div>
          </article>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Swing Liquidity</h2>
          <span>H1 Magnets | H4 Magnets | dashboard-only context</span>
        </div>

        <article class="card accent-card">
          <div id="strongest-liquidity" class="card-body empty">
            <strong>Strongest Liquidity Magnet</strong>
            No H1/H4 liquidity magnets yet.
          </div>
        </article>

        <div id="liquidity-grid" class="grid-3">
          <article class="card">
            <div class="card-body empty">
              <strong>Loading liquidity...</strong>
              ObserverAI is preparing H1 and H4 magnets.
            </div>
          </article>
        </div>
      </section>
    </section>
  </main>

  <script>
    const SUPPORTED_SYMBOLS = __SYMBOLS_JSON__;
    const REFRESH_INTERVAL_MS = 15000;
    const MAX_TRADEABLE_AGE_MS = 24 * 60 * 60 * 1000;

    const LABEL_OVERRIDES = {
      bullish_continuation: "Bullish Continuation",
      bearish_continuation: "Bearish Continuation",
      bullish_reversal: "Bullish Reversal",
      bearish_reversal: "Bearish Reversal",
      neutral_outside_value: "Neutral Outside Value",
      neutral_wait: "Neutral Wait",
      target_hit: "Target Hit",
      invalidated: "Invalidated",
      expired: "Expired",
      open: "Open",
      not_tracking: "Not Tracking",
      none: "None",
      equal_highs: "Equal Highs",
      equal_lows: "Equal Lows",
      previous_day_high: "Previous Day High",
      previous_day_low: "Previous Day Low",
      weekly_high: "Weekly High",
      weekly_low: "Weekly Low",
      round_number: "Round Number",
      imbalance: "Unfilled Imbalance"
    };

    const refreshButton = document.getElementById("refresh-btn");
    const statusNode = document.getElementById("status");
    const timerNode = document.getElementById("m15-timer");
    const bestSignalNode = document.getElementById("best-signal");
    const symbolGridNode = document.getElementById("symbol-grid");
    const strongestLiquidityNode = document.getElementById("strongest-liquidity");
    const liquidityGridNode = document.getElementById("liquidity-grid");

    let latestBySymbol = new Map();
    let liquidityBySymbol = new Map();

    function humanizeLabel(value) {
      if (!value) {
        return "None";
      }

      const normalized = String(value).trim();
      const lowered = normalized.toLowerCase();
      if (LABEL_OVERRIDES[lowered]) {
        return LABEL_OVERRIDES[lowered];
      }

      return normalized
        .split(/[_\\s]+/)
        .filter(Boolean)
        .map((part) => {
          const token = part.toLowerCase();
          if (token === "adr") return "ADR";
          if (token === "bos") return "BOS";
          if (token === "mss") return "MSS";
          if (token === "xauusd") return "XAUUSD";
          if (token === "gbpjpy") return "GBPJPY";
          if (token === "btcusd") return "BTCUSD";
          return part.charAt(0).toUpperCase() + part.slice(1);
        })
        .join(" ");
    }

    function formatNumber(value, fallback = "None") {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return fallback;
      }
      return Number(value).toFixed(2);
    }

    function formatTimestamp(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "Unknown";
      }
      return date.toLocaleString();
    }

    function formatAge(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "Unknown";
      }

      const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
      if (seconds < 60) return `${seconds}s ago`;
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.floor(minutes / 60);
      if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h ago`;
    }

    function formatAction(action) {
      if (action === "BUY") return "Buy Signal";
      if (action === "SELL") return "Sell Signal";
      return "Standby";
    }

    function actionClass(action) {
      if (action === "BUY") return "buy";
      if (action === "SELL") return "sell";
      return "wait";
    }

    function formatLifecycle(signal) {
      return signal && signal.lifecycle && signal.lifecycle.state
        ? signal.lifecycle.state
        : "Setup Forming";
    }

    function formatBias(signal) {
      return humanizeLabel(signal && signal.resolved_bias);
    }

    function formatReason(signal) {
      return signal && signal.intent && signal.intent.reason
        ? String(signal.intent.reason)
        : "No additional context available.";
    }

    function isTradeableSignal(signal) {
      if (!signal || !signal.intent) return false;
      if (!["BUY", "SELL"].includes(signal.intent.action)) return false;
      if (Number(signal.confidence || 0) < 88) return false;
      if (!signal.intent.target && signal.intent.target !== 0) return false;
      if (formatLifecycle(signal) !== "Setup Confirmed") return false;
      if (
        !String(signal.resolved_bias || "").startsWith("bullish") &&
        !String(signal.resolved_bias || "").startsWith("bearish")
      ) {
        return false;
      }

      const createdAt = new Date(signal.created_at);
      if (Number.isNaN(createdAt.getTime())) return false;
      return (Date.now() - createdAt.getTime()) <= MAX_TRADEABLE_AGE_MS;
    }

    function tradeableLabel(signal) {
      return isTradeableSignal(signal) ? "Tradeable" : "Not Tradeable";
    }

    function renderBestSignal(payload) {
      if (!payload || !payload.tradeable) {
        bestSignalNode.className = "card-body empty";
        bestSignalNode.innerHTML = `
          <strong>Best Signal Now</strong>
          ${payload && payload.message ? payload.message : "No strong signal available"}
        `;
        return;
      }

      bestSignalNode.className = "card-body";
      bestSignalNode.innerHTML = `
        <div class="headline">
          <span class="eyebrow">Best Signal Now</span>
          <div class="badge-row">
            <span class="pill">${payload.symbol}</span>
            <span class="pill ${actionClass(payload.action)}">${formatAction(payload.action)}</span>
            <span class="pill tradeable-yes">Tradeable</span>
            <span class="pill">${payload.bias}</span>
          </div>
          <p>${payload.reason || "Highest confidence active directional setup"}</p>
        </div>
        <div class="mini-grid">
          <div class="mini-row">
            <span>Confidence</span>
            <span>${payload.confidence}%</span>
          </div>
          <div class="mini-row">
            <span>Current Price</span>
            <span>${formatNumber(payload.price)}</span>
          </div>
          <div class="mini-row">
            <span>Target</span>
            <span>${formatNumber(payload.target, "Not Set")}</span>
          </div>
          <div class="mini-row">
            <span>Mode</span>
            <span>Scalping EA</span>
          </div>
        </div>
      `;
    }

    function renderSignalTiles() {
      symbolGridNode.innerHTML = SUPPORTED_SYMBOLS.map((symbol) => {
        const signal = latestBySymbol.get(symbol);
        if (!signal) {
          return `
            <article class="card">
              <div class="card-body empty">
                <strong>${symbol}</strong>
                No signals yet for this symbol.
              </div>
            </article>
          `;
        }

        const tradeable = isTradeableSignal(signal);
        return `
          <article class="card">
            <div class="card-body tile">
              <div class="tile-top">
                <span class="pill">${signal.symbol}</span>
                <span class="pill ${actionClass(signal.intent.action)}">${formatAction(signal.intent.action)}</span>
                <span class="pill ${tradeable ? "tradeable-yes" : "tradeable-no"}">${tradeableLabel(signal)}</span>
              </div>
              <div class="headline">
                <div class="section-head">
                  <h3>${formatBias(signal)}</h3>
                  <span>Lifecycle: ${formatLifecycle(signal)}</span>
                </div>
                <p>Last updated ${formatAge(signal.created_at)} | ${formatTimestamp(signal.created_at)}</p>
              </div>
              <div class="mini-grid">
                <div class="mini-row">
                  <span>Confidence</span>
                  <span>${signal.confidence}%</span>
                </div>
                <div class="mini-row">
                  <span>Price</span>
                  <span>${formatNumber(signal.current_price)}</span>
                </div>
                <div class="mini-row">
                  <span>Target</span>
                  <span>${formatNumber(signal.intent && signal.intent.target, "Not Set")}</span>
                </div>
                <div class="mini-row">
                  <span>Status</span>
                  <span>${humanizeLabel(signal.lifecycle && signal.lifecycle.outcome_status)}</span>
                </div>
              </div>
              <div class="tile-reason">${formatReason(signal)}</div>
            </div>
          </article>
        `;
      }).join("");
    }

    function flattenLiquidity() {
      const all = [];
      for (const symbol of SUPPORTED_SYMBOLS) {
        const entry = liquidityBySymbol.get(symbol);
        if (!entry) continue;
        for (const timeframe of ["H1", "H4"]) {
          const payload = entry[timeframe];
          if (!payload || !Array.isArray(payload.strong_magnets)) continue;
          for (const magnet of payload.strong_magnets) {
            all.push({ symbol, timeframe, ...magnet });
          }
        }
      }
      return all;
    }

    function renderStrongestLiquidity() {
      const magnets = flattenLiquidity();
      if (!magnets.length) {
        strongestLiquidityNode.className = "card-body empty";
        strongestLiquidityNode.innerHTML = `
          <strong>Strongest Liquidity Magnet</strong>
          No H1/H4 liquidity magnets yet.
        `;
        return;
      }

      magnets.sort((left, right) => {
        if (right.strength !== left.strength) return right.strength - left.strength;
        if (left.distance !== right.distance) return left.distance - right.distance;
        return left.rank - right.rank;
      });

      const strongest = magnets[0];
      strongestLiquidityNode.className = "card-body";
      strongestLiquidityNode.innerHTML = `
        <div class="headline">
          <span class="eyebrow">Strongest Liquidity Magnet</span>
          <div class="liquidity-top">
            <span class="pill">${strongest.symbol}</span>
            <span class="pill">${strongest.timeframe}</span>
            <span class="pill">${humanizeLabel(strongest.type)}</span>
            <span class="pill">${strongest.side === "above" ? "Above" : "Below"}</span>
          </div>
          <p>${strongest.reason}</p>
        </div>
        <div class="mini-grid">
          <div class="mini-row">
            <span>Price</span>
            <span>${formatNumber(strongest.price)}</span>
          </div>
          <div class="mini-row">
            <span>Distance</span>
            <span>${formatNumber(strongest.distance)}</span>
          </div>
          <div class="mini-row">
            <span>Strength</span>
            <span>${strongest.strength}</span>
          </div>
          <div class="mini-row">
            <span>Direction</span>
            <span>${strongest.side === "above" ? "Above" : "Below"}</span>
          </div>
        </div>
      `;
    }

    function renderMagnetList(payload, timeframe) {
      if (!payload || !Array.isArray(payload.strong_magnets) || !payload.strong_magnets.length) {
        return `
          <div class="empty">
            <strong>${timeframe} Magnets</strong>
            No ${timeframe} liquidity magnets yet for this symbol.
          </div>
        `;
      }

      return `
        <div class="liquidity-list">
          ${payload.strong_magnets.slice(0, 3).map((magnet) => `
            <article class="liquidity-item">
              <span class="liquidity-kicker">${timeframe} Magnets</span>
              <span class="liquidity-main">${magnet.rank}. ${magnet.label} ${formatNumber(magnet.price)}</span>
              <div class="liquidity-meta">
                <span>Direction: ${magnet.side === "above" ? "Above" : "Below"}</span>
                <span>Distance: ${formatNumber(magnet.distance)}</span>
                <span>Strength: ${magnet.strength}</span>
              </div>
              <div class="liquidity-reason">${magnet.reason}</div>
            </article>
          `).join("")}
        </div>
      `;
    }

    function renderLiquidityTiles() {
      liquidityGridNode.innerHTML = SUPPORTED_SYMBOLS.map((symbol) => {
        const entry = liquidityBySymbol.get(symbol);
        const h1 = entry ? entry.H1 : null;
        const h4 = entry ? entry.H4 : null;
        const hasAny = Boolean(
          (h1 && h1.strong_magnets && h1.strong_magnets.length) ||
          (h4 && h4.strong_magnets && h4.strong_magnets.length)
        );

        if (!hasAny) {
          return `
            <article class="card">
              <div class="card-body empty">
                <strong>${symbol}</strong>
                No H1/H4 liquidity magnets yet for this symbol.
              </div>
            </article>
          `;
        }

        return `
          <article class="card">
            <div class="card-body liquidity-card">
              <div class="section-head">
                <h3>${symbol}</h3>
                <span>HTF Bias: ${entry && entry.htf_magnet_bias ? humanizeLabel(entry.htf_magnet_bias) : "Neutral"}</span>
              </div>
              <div class="grid-2">
                <div>${renderMagnetList(h1, "H1")}</div>
                <div>${renderMagnetList(h4, "H4")}</div>
              </div>
            </div>
          </article>
        `;
      }).join("");
    }

    function updateM15Timer() {
      const now = new Date();
      const elapsed = (now.getMinutes() % 15) * 60 + now.getSeconds();
      const remaining = elapsed === 0 ? 15 * 60 : (15 * 60) - elapsed;
      const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
      const seconds = String(remaining % 60).padStart(2, "0");
      timerNode.textContent = `Next M15 close in: ${minutes}:${seconds}`;
    }

    function refreshAges() {
      if (latestBySymbol.size) {
        renderSignalTiles();
      }
    }

    async function loadDashboard() {
      statusNode.textContent = "Loading multi-symbol signals and liquidity...";

      try {
        const requests = [
          fetch("/signals/best"),
          ...SUPPORTED_SYMBOLS.map((symbol) => fetch(`/signals/latest?symbol=${encodeURIComponent(symbol)}&limit=1`)),
          ...SUPPORTED_SYMBOLS.flatMap((symbol) => [
            fetch(`/liquidity/magnets?symbol=${encodeURIComponent(symbol)}&timeframe=H1`),
            fetch(`/liquidity/magnets?symbol=${encodeURIComponent(symbol)}&timeframe=H4`)
          ])
        ];

        const responses = await Promise.all(requests);
        const bestResponse = responses[0];
        const latestResponses = responses.slice(1, 1 + SUPPORTED_SYMBOLS.length);
        const liquidityResponses = responses.slice(1 + SUPPORTED_SYMBOLS.length);

        if (!bestResponse.ok) {
          throw new Error(`Best signal request failed with HTTP ${bestResponse.status}.`);
        }

        renderBestSignal(await bestResponse.json());

        latestBySymbol = new Map();
        for (let index = 0; index < latestResponses.length; index += 1) {
          const response = latestResponses[index];
          const symbol = SUPPORTED_SYMBOLS[index];
          if (!response.ok) continue;
          const payload = await response.json();
          const item = Array.isArray(payload.items) && payload.items.length ? payload.items[0] : null;
          if (item) {
            latestBySymbol.set(symbol, item);
          }
        }
        renderSignalTiles();

        liquidityBySymbol = new Map();
        for (let index = 0; index < liquidityResponses.length; index += 2) {
          const symbol = SUPPORTED_SYMBOLS[index / 2];
          const h1Response = liquidityResponses[index];
          const h4Response = liquidityResponses[index + 1];
          const symbolEntry = { H1: null, H4: null, htf_magnet_bias: "neutral" };

          if (h1Response && h1Response.ok) {
            symbolEntry.H1 = await h1Response.json();
          }
          if (h4Response && h4Response.ok) {
            symbolEntry.H4 = await h4Response.json();
          }

          const biases = [symbolEntry.H1 && symbolEntry.H1.htf_magnet_bias, symbolEntry.H4 && symbolEntry.H4.htf_magnet_bias].filter(Boolean);
          if (biases.includes("bullish") && !biases.includes("bearish")) {
            symbolEntry.htf_magnet_bias = "bullish";
          } else if (biases.includes("bearish") && !biases.includes("bullish")) {
            symbolEntry.htf_magnet_bias = "bearish";
          }

          liquidityBySymbol.set(symbol, symbolEntry);
        }

        renderStrongestLiquidity();
        renderLiquidityTiles();
        statusNode.textContent = `Loaded ${SUPPORTED_SYMBOLS.length} symbols | Auto-refresh every 15s`;
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error.";
        bestSignalNode.className = "card-body empty";
        bestSignalNode.innerHTML = `
          <strong>Best Signal Now</strong>
          ${message}
        `;
        strongestLiquidityNode.className = "card-body empty";
        strongestLiquidityNode.innerHTML = `
          <strong>Strongest Liquidity Magnet</strong>
          Liquidity view is temporarily unavailable.
        `;
        latestBySymbol = new Map();
        liquidityBySymbol = new Map();
        renderSignalTiles();
        renderLiquidityTiles();
        statusNode.textContent = "Dashboard refresh failed";
      }
    }

    refreshButton.addEventListener("click", loadDashboard);

    updateM15Timer();
    loadDashboard();
    window.setInterval(loadDashboard, REFRESH_INTERVAL_MS);
    window.setInterval(updateM15Timer, 1000);
    window.setInterval(refreshAges, 1000);
  </script>
</body>
</html>
"""
    return HTMLResponse(html.replace("__SYMBOLS_JSON__", symbols_json))
