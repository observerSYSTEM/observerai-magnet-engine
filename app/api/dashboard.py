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
  <title>ObserverAI Dashboard v2</title>
  <style>
    :root {
      --bg: #f5f3ef;
      --panel: #ffffff;
      --panel-soft: #faf8f4;
      --ink: #15191f;
      --muted: #69707c;
      --line: #d8d2c6;
      --accent: #8c7550;
      --buy: #225c42;
      --sell: #8b4136;
      --wait: #7c6b44;
      --shadow: 0 18px 44px rgba(21, 25, 31, 0.06);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }

    .shell {
      width: min(1200px, calc(100% - 28px));
      margin: 0 auto;
      padding: 28px 0 56px;
      display: grid;
      gap: 18px;
    }

    .masthead {
      display: grid;
      gap: 10px;
    }

    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
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
      font-size: clamp(30px, 4vw, 42px);
      line-height: 1.1;
    }

    h2 {
      font-size: 24px;
      line-height: 1.2;
    }

    h3 {
      font-size: 18px;
      line-height: 1.25;
    }

    .subhead {
      margin: 0;
      max-width: 900px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.7;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.86);
      box-shadow: var(--shadow);
    }

    .toolbar-group {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }

    select,
    button {
      min-height: 40px;
      padding: 0 14px;
      border-radius: 999px;
      font: inherit;
      font-size: 14px;
    }

    select {
      border: 1px solid var(--line);
      background: var(--panel-soft);
      color: var(--ink);
    }

    button {
      border: 0;
      background: var(--ink);
      color: #f8f7f3;
      font-weight: 700;
      cursor: pointer;
    }

    .status,
    .timer {
      font-size: 13px;
      color: var(--muted);
    }

    .timer {
      color: var(--accent);
      font-weight: 700;
    }

    .stack,
    .section {
      display: grid;
      gap: 16px;
    }

    .section-head {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
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
      padding: 20px;
      display: grid;
      gap: 14px;
    }

    .accent-card {
      background: linear-gradient(180deg, rgba(250, 248, 244, 0.96), rgba(255, 255, 255, 1));
    }

    .grid-4,
    .grid-3,
    .grid-2 {
      display: grid;
      gap: 14px;
    }

    .grid-4 {
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .grid-3 {
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }

    .grid-2 {
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    }

    .metric,
    .tile,
    .stock-row {
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.92);
      display: grid;
      gap: 8px;
    }

    .metric-label,
    .tile-label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .metric-value,
    .tile-value {
      font-size: 18px;
      line-height: 1.35;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .pill {
      padding: 8px 11px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .buy { color: var(--buy); }
    .sell { color: var(--sell); }
    .wait { color: var(--wait); }
    .reason,
    .muted {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
      white-space: normal;
      overflow-wrap: anywhere;
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
        width: min(100%, calc(100% - 20px));
      }

      .card-body {
        padding: 18px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="masthead">
      <span class="eyebrow">ObserverAI Magnet Engine v2</span>
      <h1>Institutional Bias, Liquidity, News, and Opportunity Context</h1>
      <p class="subhead">
        The scalping engine stays strict around M1 and M15 execution, while the dashboard expands into 08:01 bias, higher-timeframe liquidity, volatility, manipulation context, and weekly opportunity scanning.
      </p>
    </section>

    <section class="toolbar">
      <div class="toolbar-group">
        <label class="status" for="symbol-select">Symbol</label>
        <select id="symbol-select"></select>
        <button id="refresh-btn" type="button">Refresh</button>
      </div>
      <div class="toolbar-group">
        <span id="m15-timer" class="timer">Next M15 close in: 15:00</span>
        <span id="status" class="status">Waiting for data...</span>
      </div>
    </section>

    <section class="stack">
      <article class="card accent-card">
        <div id="best-direction" class="card-body empty">
          <strong>Best Direction Now</strong>
          No strong directional alignment yet.
        </div>
      </article>

      <section class="section">
        <div class="section-head">
          <h2>Multi-Symbol Overview</h2>
          <span>XAUUSD | GBPJPY | BTCUSD</span>
        </div>
        <div id="symbol-tiles" class="grid-3">
          <article class="card"><div class="card-body empty"><strong>Loading symbols...</strong>ObserverAI is preparing the latest v2 summaries.</div></article>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Selected Symbol</h2>
          <span id="selected-symbol-label">XAUUSD</span>
        </div>
        <div class="grid-2">
          <article class="card">
            <div id="anchor-card" class="card-body empty"><strong>08:01 Anchor</strong>No anchor data yet.</div>
          </article>
          <article class="card">
            <div id="zone-card" class="card-body empty"><strong>Zone-to-Zone Liquidity</strong>No liquidity path yet.</div>
          </article>
          <article class="card">
            <div id="midlevel-card" class="card-body empty"><strong>M15 Midlevel Break</strong>No M15 midlevel break yet.</div>
          </article>
          <article class="card">
            <div id="volatility-card" class="card-body empty"><strong>Volatility + Manipulation</strong>No volatility snapshot yet.</div>
          </article>
          <article class="card">
            <div id="news-card" class="card-body empty"><strong>News Direction</strong>No news context loaded yet.</div>
          </article>
          <article class="card">
            <div id="scalp-card" class="card-body empty"><strong>Scalp Status</strong>No signals yet for this symbol.</div>
          </article>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>Weekly Stock Opportunities</h2>
          <span>Elite dashboard context</span>
        </div>
        <article class="card">
          <div id="stocks-card" class="card-body empty">
            <strong>Weekly Stock Opportunities</strong>
            Stock data is loading.
          </div>
        </article>
      </section>
    </section>
  </main>

  <script>
    const SUPPORTED_SYMBOLS = __SYMBOLS_JSON__;
    const REFRESH_INTERVAL_MS = 15000;
    const LABEL_OVERRIDES = {
      bullish: "Bullish",
      bearish: "Bearish",
      neutral: "Neutral",
      buy: "Buy",
      sell: "Sell",
      wait: "Wait",
      wick_rejection: "Wick Rejection",
      body_acceptance: "Body Acceptance",
      buy_side_sweep: "Buy-Side Sweep",
      sell_side_sweep: "Sell-Side Sweep",
      range_trap: "Range Trap",
      no_mid_flow: "No Mid Flow",
      bullish_mid_to_mid: "Bullish Mid-to-Mid",
      bearish_mid_to_mid: "Bearish Mid-to-Mid",
      mid_compression: "Mid Compression",
      break_up: "Break Up",
      break_down: "Break Down",
      equal_highs: "Equal Highs",
      equal_lows: "Equal Lows",
      previous_day_high: "Previous Day High",
      previous_day_low: "Previous Day Low",
      weekly_high: "Weekly High",
      weekly_low: "Weekly Low",
      round_number: "Round Number",
      imbalance: "Unfilled Imbalance",
      setup_confirmed: "Setup Confirmed",
      setup_forming: "Setup Forming"
    };

    const state = {
      selectedSymbol: SUPPORTED_SYMBOLS[0] || "XAUUSD"
    };

    function humanizeLabel(value) {
      if (value === null || value === undefined || value === "") {
        return "None";
      }
      const raw = String(value).trim();
      const lower = raw.toLowerCase();
      if (LABEL_OVERRIDES[lower]) {
        return LABEL_OVERRIDES[lower];
      }
      return raw
        .replace(/_/g, " ")
        .replace(/\\b\\w/g, (match) => match.toUpperCase());
    }

    function formatPrice(value) {
      if (value === null || value === undefined) {
        return "None";
      }
      const number = Number(value);
      if (!Number.isFinite(number)) {
        return "None";
      }
      if (Math.abs(number) >= 1000) {
        return number.toFixed(2);
      }
      return number.toFixed(5);
    }

    function formatMagnetValue(magnet) {
      if (!magnet) {
        return "None";
      }
      return `${humanizeLabel(magnet.name)} ${formatPrice(magnet.price)}`;
    }

    function formatAge(value) {
      if (!value) {
        return "Unknown";
      }
      const ms = Date.now() - new Date(value).getTime();
      if (!Number.isFinite(ms) || ms < 0) {
        return "Just now";
      }
      const totalSeconds = Math.floor(ms / 1000);
      if (totalSeconds < 60) {
        return `${totalSeconds}s ago`;
      }
      const totalMinutes = Math.floor(totalSeconds / 60);
      if (totalMinutes < 60) {
        return `${totalMinutes}m ago`;
      }
      const totalHours = Math.floor(totalMinutes / 60);
      if (totalHours < 24) {
        return `${totalHours}h ago`;
      }
      return `${Math.floor(totalHours / 24)}d ago`;
    }

    function actionClass(value) {
      const lower = String(value || "").toLowerCase();
      if (lower.includes("buy") || lower.includes("bullish")) return "buy";
      if (lower.includes("sell") || lower.includes("bearish")) return "sell";
      return "wait";
    }

    function renderBestDirection(summary) {
      const root = document.getElementById("best-direction");
      const item = summary && summary.best_direction_now;
      if (!item || !item.symbol) {
        root.className = "card-body empty";
        root.innerHTML = "<strong>Best Direction Now</strong>No strong directional alignment yet.";
        return;
      }

      root.className = "card-body";
      root.innerHTML = `
        <div class="pill-row">
          <span class="pill ${actionClass(item.direction)}">${humanizeLabel(item.direction)}</span>
          <span class="pill">${item.symbol}</span>
          <span class="pill">${item.confidence}% Confidence</span>
          <span class="pill">${humanizeLabel(item.trade_policy)}</span>
        </div>
        <div class="grid-4">
          <div class="metric">
            <span class="metric-label">Symbol</span>
            <span class="metric-value">${item.symbol}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Highest Probability Direction</span>
            <span class="metric-value ${actionClass(item.direction)}">${humanizeLabel(item.direction)}</span>
          </div>
          <div class="metric">
            <span class="metric-label">08:01 Bias</span>
            <span class="metric-value">${humanizeLabel(item.anchor_bias)}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Current Price</span>
            <span class="metric-value">${formatPrice(item.current_price)}</span>
          </div>
        </div>
      `;
    }

    function renderSymbolTiles(summary) {
      const root = document.getElementById("symbol-tiles");
      const items = summary && Array.isArray(summary.symbols) ? summary.symbols : [];
      if (!items.length) {
        root.innerHTML = '<article class="card"><div class="card-body empty"><strong>No signals yet</strong>No symbols are ready yet.</div></article>';
        return;
      }

      root.innerHTML = items.map((item) => {
        const scalp = item.scalp_signal;
        return `
          <article class="card">
            <div class="card-body tile">
              <div class="pill-row">
                <span class="pill">${item.symbol}</span>
                <span class="pill ${actionClass(item.highest_probability_direction.direction)}">${humanizeLabel(item.highest_probability_direction.direction)}</span>
                <span class="pill">${humanizeLabel(item.volatility_state)}</span>
              </div>
              <div class="grid-2">
                <div class="metric">
                  <span class="metric-label">08:01 Bias</span>
                  <span class="metric-value">${humanizeLabel(item.anchor_bias)}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Strongest H1/H4 Magnet</span>
                  <span class="metric-value">${item.strongest_magnet ? `${item.strongest_magnet.label} ${formatPrice(item.strongest_magnet.price)}` : "No magnet yet"}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Scalp Status</span>
                  <span class="metric-value ${actionClass(scalp && scalp.action)}">${scalp ? `${humanizeLabel(scalp.action)} | ${humanizeLabel(scalp.lifecycle)}` : "No signals yet for this symbol."}</span>
                </div>
                <div class="metric">
                  <span class="metric-label">Tradeable</span>
                  <span class="metric-value">${scalp && scalp.tradeable ? "Tradeable" : "Not Tradeable"}</span>
                </div>
              </div>
              <p class="reason">${item.highest_probability_direction.reason}</p>
            </div>
          </article>
        `;
      }).join("");
    }

    function renderAnchor(intelligence) {
      const anchor = intelligence.anchor_0801 || {};
      const discount = intelligence.discount_premium || {};
      const root = document.getElementById("anchor-card");
      root.className = "card-body";
      root.innerHTML = `
        <h3>08:01 Anchor</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">Anchor High</span><span class="metric-value">${formatPrice(anchor.anchor_high)}</span></div>
          <div class="metric"><span class="metric-label">Anchor Low</span><span class="metric-value">${formatPrice(anchor.anchor_low)}</span></div>
          <div class="metric"><span class="metric-label">Anchor Midlevel</span><span class="metric-value">${formatPrice(anchor.anchor_mid)}</span></div>
          <div class="metric"><span class="metric-label">Price Position</span><span class="metric-value">${humanizeLabel(discount.price_position)}</span></div>
          <div class="metric"><span class="metric-label">Bias</span><span class="metric-value ${actionClass(anchor.bias)}">${humanizeLabel(anchor.bias)}</span></div>
          <div class="metric"><span class="metric-label">Anchor Type</span><span class="metric-value">${humanizeLabel(anchor.anchor_type)}</span></div>
        </div>
        <p class="reason">${anchor.reason || "No anchor context available."}</p>
      `;
    }

    function renderZone(intelligence) {
      const liquidity = intelligence.liquidity_magnets || {};
      const zone = intelligence.zone_to_zone || {};
      const root = document.getElementById("zone-card");
      const path = Array.isArray(zone.path) ? zone.path : [];
      root.className = "card-body";
      root.innerHTML = `
        <h3>Zone-to-Zone Liquidity</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">From Current Price</span><span class="metric-value">${formatPrice(zone.from_zone)}</span></div>
          <div class="metric"><span class="metric-label">Next Zone</span><span class="metric-value">${zone.next_zone ? formatPrice(zone.next_zone) : "No valid zone"}</span></div>
          <div class="metric"><span class="metric-label">Major Zone</span><span class="metric-value">${zone.major_zone ? formatPrice(zone.major_zone) : "No valid zone"}</span></div>
          <div class="metric"><span class="metric-label">Direction</span><span class="metric-value">${humanizeLabel(zone.direction)}</span></div>
          <div class="metric"><span class="metric-label">HTF Magnet</span><span class="metric-value">${liquidity.strongest_magnet ? `${liquidity.strongest_magnet.timeframe} ${liquidity.strongest_magnet.label} ${formatPrice(liquidity.strongest_magnet.price)}` : "No magnet yet"}</span></div>
          <div class="metric"><span class="metric-label">HTF Bias</span><span class="metric-value">${humanizeLabel(liquidity.htf_magnet_bias)}</span></div>
        </div>
        <p class="reason">${path.length ? path.map((item) => `${item.label} ${formatPrice(item.price)}`).join(" -> ") : "No path available yet."}</p>
      `;
    }

    function renderMidlevel(intelligence) {
      const item = intelligence.m15_midlevel_break || {};
      const root = document.getElementById("midlevel-card");
      root.className = "card-body";
      root.innerHTML = `
        <h3>M15 Midlevel Break</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">Midlevel</span><span class="metric-value">${formatPrice(item.midlevel)}</span></div>
          <div class="metric"><span class="metric-label">Break Status</span><span class="metric-value">${item.confirmed ? "Confirmed" : "Unconfirmed"}</span></div>
          <div class="metric"><span class="metric-label">Confirmed Direction</span><span class="metric-value ${actionClass(item.direction)}">${humanizeLabel(item.direction)}</span></div>
          <div class="metric"><span class="metric-label">Next Level</span><span class="metric-value">${item.next_level ? formatPrice(item.next_level) : "No valid next level"}</span></div>
        </div>
        <p class="reason">${item.reason || "No confirmed M15 midlevel break."}</p>
      `;
    }

    function renderVolatility(intelligence) {
      const volatility = intelligence.volatility || {};
      const manipulation = intelligence.manipulation_zone || {};
      const root = document.getElementById("volatility-card");
      root.className = "card-body";
      root.innerHTML = `
        <h3>Volatility + Manipulation</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">ATR</span><span class="metric-value">${formatPrice(volatility.atr)}</span></div>
          <div class="metric"><span class="metric-label">ADR Used %</span><span class="metric-value">${Number(volatility.adr_used_pct || 0).toFixed(2)}%</span></div>
          <div class="metric"><span class="metric-label">Volatility State</span><span class="metric-value">${humanizeLabel(volatility.state)}</span></div>
          <div class="metric"><span class="metric-label">Manipulation Zone</span><span class="metric-value">${manipulation.active ? humanizeLabel(manipulation.type) : "Inactive"}</span></div>
          <div class="metric"><span class="metric-label">Zone High</span><span class="metric-value">${formatPrice(manipulation.zone_high)}</span></div>
          <div class="metric"><span class="metric-label">Zone Low</span><span class="metric-value">${formatPrice(manipulation.zone_low)}</span></div>
        </div>
      `;
    }

    function renderNews(intelligence) {
      const news = intelligence.news_context || {};
      const root = document.getElementById("news-card");
      root.className = "card-body";
      root.innerHTML = `
        <h3>News Direction</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">Event</span><span class="metric-value">${news.event || "No high-impact event tracked"}</span></div>
          <div class="metric"><span class="metric-label">Currency</span><span class="metric-value">${news.currency || "None"}</span></div>
          <div class="metric"><span class="metric-label">Time</span><span class="metric-value">${news.time ? new Date(news.time).toLocaleString() : "Not scheduled"}</span></div>
          <div class="metric"><span class="metric-label">Impact</span><span class="metric-value">${humanizeLabel(news.impact)}</span></div>
          <div class="metric"><span class="metric-label">Expected Direction</span><span class="metric-value">${humanizeLabel(news.expected_direction)}</span></div>
          <div class="metric"><span class="metric-label">Trade Policy</span><span class="metric-value">${humanizeLabel(news.trade_policy)}</span></div>
        </div>
      `;
    }

    function renderScalp(summary, intelligence) {
      const root = document.getElementById("scalp-card");
      const item = summary.symbols.find((entry) => entry.symbol === state.selectedSymbol);
      const scalp = item && item.scalp_signal;
      const best = intelligence.highest_probability_direction || {};

      if (!scalp) {
        root.className = "card-body empty";
        root.innerHTML = "<strong>Scalp Status</strong>No signals yet for this symbol.";
        return;
      }

      root.className = "card-body";
      root.innerHTML = `
        <h3>Scalp Status</h3>
        <div class="grid-2">
          <div class="metric"><span class="metric-label">Action</span><span class="metric-value ${actionClass(scalp.action)}">${humanizeLabel(scalp.action)}</span></div>
          <div class="metric"><span class="metric-label">Lifecycle</span><span class="metric-value">${humanizeLabel(scalp.lifecycle)}</span></div>
          <div class="metric"><span class="metric-label">Confidence</span><span class="metric-value">${scalp.confidence || 0}%</span></div>
          <div class="metric"><span class="metric-label">Liquidity Target</span><span class="metric-value">${scalp.dashboard_target ? formatPrice(scalp.dashboard_target) : (scalp.target ? formatPrice(scalp.target) : "None")}</span></div>
          <div class="metric"><span class="metric-label">Tradeable</span><span class="metric-value">${scalp.tradeable ? "Tradeable" : "Not Tradeable"}</span></div>
          <div class="metric"><span class="metric-label">Time Since Signal</span><span class="metric-value">${formatAge(scalp.created_at)}</span></div>
          <div class="metric"><span class="metric-label">EA TP</span><span class="metric-value">${scalp.ea_tp ? formatPrice(scalp.ea_tp) : "None"}</span></div>
          <div class="metric"><span class="metric-label">Target Type</span><span class="metric-value">${humanizeLabel(scalp.target_type)}</span></div>
          <div class="metric"><span class="metric-label">Nearest Magnet</span><span class="metric-value">${formatMagnetValue(scalp.nearest_magnet)}</span></div>
          <div class="metric"><span class="metric-label">Major Magnet</span><span class="metric-value">${formatMagnetValue(scalp.major_magnet)}</span></div>
          <div class="metric"><span class="metric-label">HTF Magnet</span><span class="metric-value">${intelligence.liquidity_magnets && intelligence.liquidity_magnets.strongest_magnet ? `${intelligence.liquidity_magnets.strongest_magnet.label} ${formatPrice(intelligence.liquidity_magnets.strongest_magnet.price)}` : "No magnet yet"}</span></div>
          <div class="metric"><span class="metric-label">Final Bias Target</span><span class="metric-value">${scalp.liquidity_target ? formatPrice(scalp.liquidity_target) : "None"}</span></div>
        </div>
        <p class="reason">${best.reason || "No scalp rationale available."}</p>
      `;
    }

    function renderStocks(payload) {
      const root = document.getElementById("stocks-card");
      if (!payload || payload.available === false || !Array.isArray(payload.opportunities) || !payload.opportunities.length) {
        root.className = "card-body empty";
        root.innerHTML = `<strong>Weekly Stock Opportunities</strong>${payload && payload.message ? payload.message : "No stock opportunities available yet."}`;
        return;
      }

      root.className = "card-body";
      root.innerHTML = `
        <h3>Weekly Stock Opportunities</h3>
        <div class="grid-3">
          ${payload.opportunities.slice(0, 6).map((item) => `
            <div class="stock-row">
              <div class="pill-row">
                <span class="pill">${item.symbol}</span>
                <span class="pill ${actionClass(item.bias)}">${humanizeLabel(item.bias)}</span>
                <span class="pill">${item.confidence}%</span>
              </div>
              <div class="muted">${humanizeLabel(item.setup_type)}</div>
              <div class="tile-value">${item.target_zone}</div>
              <div class="reason">${item.reason}</div>
              <div class="muted">${item.risk_note}</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderIntelligence(summary, intelligence) {
      document.getElementById("selected-symbol-label").textContent = state.selectedSymbol;
      renderAnchor(intelligence);
      renderZone(intelligence);
      renderMidlevel(intelligence);
      renderVolatility(intelligence);
      renderNews(intelligence);
      renderScalp(summary, intelligence);
    }

    async function loadDashboard() {
      const status = document.getElementById("status");
      status.textContent = "Refreshing...";

      try {
        const [summaryRes, intelligenceRes, stocksRes] = await Promise.all([
          fetch("/v2/dashboard-summary"),
          fetch(`/v2/intelligence?symbol=${encodeURIComponent(state.selectedSymbol)}`),
          fetch("/stocks/weekly-opportunities")
        ]);

        const summary = await summaryRes.json();
        const intelligence = await intelligenceRes.json();
        const stocks = await stocksRes.json();

        renderBestDirection(summary);
        renderSymbolTiles(summary);
        renderIntelligence(summary, intelligence);
        renderStocks(stocks);
        status.textContent = `Updated ${new Date().toLocaleTimeString()}`;
      } catch (error) {
        console.error(error);
        status.textContent = "Refresh failed. Retrying soon.";
      }
    }

    function updateM15Timer() {
      const now = new Date();
      const next = new Date(now);
      next.setSeconds(0, 0);
      const minutes = now.getMinutes();
      next.setMinutes(minutes - (minutes % 15) + 15);
      const diff = Math.max(0, next.getTime() - now.getTime());
      const totalSeconds = Math.floor(diff / 1000);
      const mm = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
      const ss = String(totalSeconds % 60).padStart(2, "0");
      document.getElementById("m15-timer").textContent = `Next M15 close in: ${mm}:${ss}`;
    }

    function initialise() {
      const select = document.getElementById("symbol-select");
      select.innerHTML = SUPPORTED_SYMBOLS.map((symbol) => `<option value="${symbol}">${symbol}</option>`).join("");
      select.value = state.selectedSymbol;
      select.addEventListener("change", () => {
        state.selectedSymbol = select.value;
        loadDashboard();
      });

      document.getElementById("refresh-btn").addEventListener("click", loadDashboard);
      updateM15Timer();
      loadDashboard();
      setInterval(loadDashboard, REFRESH_INTERVAL_MS);
      setInterval(updateM15Timer, 1000);
    }

    initialise();
  </script>
</body>
</html>
""".replace("__SYMBOLS_JSON__", symbols_json)
    return HTMLResponse(html)
