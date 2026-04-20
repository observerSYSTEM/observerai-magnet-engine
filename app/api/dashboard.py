from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def signals_dashboard() -> HTMLResponse:
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ObserverAI Signals Dashboard</title>
  <style>
    :root {
      --bg: #f4efe6;
      --panel: #fffdf8;
      --panel-soft: #f8f1e6;
      --ink: #1f1d1a;
      --muted: #6a645d;
      --line: #d8cfc0;
      --accent: #8b5e34;
      --buy: #1d6b45;
      --sell: #9f3427;
      --wait: #836a2a;
      --shadow: 0 18px 44px rgba(71, 51, 27, 0.08);
      --shadow-soft: 0 8px 24px rgba(71, 51, 27, 0.06);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(139, 94, 52, 0.12), transparent 28%),
        linear-gradient(180deg, #f8f3ea 0%, var(--bg) 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }

    .hero {
      display: grid;
      gap: 12px;
      margin-bottom: 24px;
    }

    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    h1 {
      margin: 0;
      font-size: clamp(32px, 5vw, 54px);
      line-height: 0.95;
      font-weight: 600;
    }

    .subhead {
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      max-width: 760px;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      padding: 14px 16px;
      background: rgba(255, 253, 248, 0.86);
      border: 1px solid rgba(216, 207, 192, 0.9);
      border-radius: 18px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    label {
      font-size: 13px;
      color: var(--muted);
    }

    input {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 10px 12px;
      border-radius: 999px;
      min-width: 132px;
      font: inherit;
    }

    button {
      border: 0;
      background: var(--accent);
      color: white;
      padding: 10px 16px;
      border-radius: 999px;
      font: inherit;
      cursor: pointer;
      transition: transform 140ms ease, opacity 140ms ease;
    }

    button:hover {
      opacity: 0.92;
      transform: translateY(-1px);
    }

    .status {
      font-size: 13px;
      color: var(--muted);
    }

    .grid {
      display: grid;
      gap: 20px;
    }

    .overview-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(300px, 1fr);
      gap: 20px;
      align-items: start;
    }

    .card {
      background: var(--panel);
      border: 1px solid rgba(216, 207, 192, 0.94);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .card-body {
      padding: 22px;
    }

    .latest-card {
      position: relative;
      background:
        linear-gradient(135deg, rgba(248, 241, 230, 0.96), rgba(255, 253, 248, 0.98)),
        var(--panel);
    }

    .latest-card::after {
      content: "";
      position: absolute;
      inset: auto -48px -48px auto;
      width: 180px;
      height: 180px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(139, 94, 52, 0.16), transparent 65%);
      pointer-events: none;
    }

    .performance-card {
      background:
        linear-gradient(180deg, rgba(248, 241, 230, 0.95), rgba(255, 253, 248, 0.98)),
        var(--panel);
    }

    .topline {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 20px;
      position: relative;
      z-index: 1;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: var(--panel-soft);
      color: var(--accent);
      border: 1px solid rgba(216, 207, 192, 0.75);
    }

    .action-badge {
      font-size: 15px;
      font-weight: 700;
      padding: 10px 16px;
      box-shadow: var(--shadow-soft);
    }

    .bias-badge {
      font-size: 13px;
      font-weight: 600;
      padding: 9px 14px;
    }

    .confidence-badge {
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 700;
      box-shadow: var(--shadow-soft);
    }

    .action-buy, .confidence-high { color: var(--buy); }
    .action-sell, .confidence-low { color: var(--sell); }
    .action-wait, .confidence-medium { color: var(--wait); }

    .headline {
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
      position: relative;
      z-index: 1;
    }

    .headline h2 {
      margin: 0;
      font-size: clamp(30px, 4vw, 46px);
      line-height: 0.95;
      font-weight: 600;
    }

    .headline p {
      margin: 0;
      color: var(--muted);
      font-size: 15px;
      max-width: 700px;
    }

    .signal-age {
      font-weight: 700;
      color: var(--accent);
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      position: relative;
      z-index: 1;
    }

    .metric {
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(216, 207, 192, 0.84);
    }

    .metric-label {
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
    }

    .metric-value {
      display: block;
      font-size: 22px;
      line-height: 1;
    }

    .details-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
      position: relative;
      z-index: 1;
    }

    .context-block {
      display: grid;
      gap: 12px;
      margin-top: 16px;
      position: relative;
      z-index: 1;
    }

    .context-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
    }

    .detail-card {
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.58);
      border: 1px solid rgba(216, 207, 192, 0.8);
    }

    .context-card {
      padding: 13px 15px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.64);
      border: 1px solid rgba(216, 207, 192, 0.82);
      box-shadow: var(--shadow-soft);
    }

    .detail-label {
      display: block;
      margin-bottom: 7px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .detail-value {
      display: block;
      font-size: 17px;
      line-height: 1.25;
    }

    .detail-subvalue {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.35;
    }

    .mid-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }

    .path-summary {
      display: grid;
      gap: 10px;
      padding: 15px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.64);
      border: 1px solid rgba(216, 207, 192, 0.82);
      box-shadow: var(--shadow-soft);
    }

    .path-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .path-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(248, 241, 230, 0.96);
      border: 1px solid rgba(216, 207, 192, 0.9);
      color: var(--ink);
      font-size: 13px;
      line-height: 1;
      white-space: nowrap;
    }

    .path-rank {
      color: var(--accent);
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .path-arrow {
      color: var(--muted);
      font-size: 14px;
    }

    .path-empty {
      color: var(--muted);
      font-size: 14px;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-top: 8px;
    }

    .section-head h3 {
      margin: 0;
      font-size: 19px;
    }

    .section-head span {
      color: var(--muted);
      font-size: 13px;
    }

    .performance-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }

    .performance-metric {
      padding: 14px 15px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(216, 207, 192, 0.84);
    }

    .performance-metric .metric-value {
      font-size: 20px;
    }

    .performance-note {
      margin: 16px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    .signal-list {
      display: grid;
      gap: 14px;
      margin-top: 14px;
    }

    .signal-item {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 2fr);
      gap: 16px;
      padding: 16px 18px;
      border-top: 1px solid rgba(216, 207, 192, 0.88);
    }

    .signal-item:first-child {
      border-top: 0;
    }

    .signal-main,
    .signal-meta {
      display: grid;
      gap: 8px;
    }

    .signal-title {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .signal-title strong {
      font-size: 18px;
    }

    .signal-meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 10px 14px;
      color: var(--muted);
      font-size: 14px;
    }

    .empty {
      padding: 32px 22px;
      color: var(--muted);
      text-align: center;
    }

    .empty strong {
      display: block;
      color: var(--ink);
      font-size: 20px;
      margin-bottom: 8px;
    }

    @media (max-width: 900px) {
      .overview-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 780px) {
      .performance-grid {
        grid-template-columns: 1fr 1fr;
      }

      .signal-item {
        grid-template-columns: 1fr;
      }

      .card-body {
        padding: 18px;
      }

      .toolbar {
        border-radius: 16px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">ObserverAI Magnet Engine</span>
      <h1>Signals Dashboard</h1>
      <p class="subhead">
        Live monitoring view for the latest stored signal, recent history, and performance summary from
        <code>/signals/latest</code> and <code>/performance/summary</code>.
      </p>
    </section>

    <section class="toolbar">
      <div class="toolbar-group">
        <label for="symbol-input">Symbol</label>
        <input id="symbol-input" type="text" value="XAUUSD" />
        <button id="refresh-btn" type="button">Refresh</button>
      </div>
      <div class="toolbar-group">
        <span id="status" class="status">Waiting for data...</span>
      </div>
    </section>

    <section class="grid">
      <section class="overview-grid">
        <article class="card latest-card">
          <div id="latest-signal" class="card-body empty">
            <strong>No signals yet</strong>
            Start the runner and store a signal to populate the live dashboard.
          </div>
        </article>

        <article class="card performance-card">
          <div id="performance-summary" class="card-body empty">
            <strong>No performance data yet</strong>
            Performance metrics will appear once stored signals begin tracking outcomes.
          </div>
        </article>
      </section>

      <article class="card">
        <div class="card-body">
          <div class="section-head">
            <h3>Recent Signals</h3>
            <span id="recent-count">0 signals</span>
          </div>
          <div id="recent-signals" class="signal-list">
            <div class="empty">
              <strong>History is empty</strong>
              Recent signals will appear here automatically once the engine has activity.
            </div>
          </div>
        </div>
      </article>
    </section>
  </main>

  <script>
    const symbolInput = document.getElementById("symbol-input");
    const refreshButton = document.getElementById("refresh-btn");
    const statusNode = document.getElementById("status");
    const latestNode = document.getElementById("latest-signal");
    const performanceNode = document.getElementById("performance-summary");
    const recentNode = document.getElementById("recent-signals");
    const recentCountNode = document.getElementById("recent-count");

    function formatNumber(value) {
      if (value === null || value === undefined) {
        return "none";
      }
      return Number(value).toFixed(2);
    }

    function formatDecimal(value) {
      if (value === null || value === undefined) {
        return "0.00";
      }
      return Number(value).toFixed(2);
    }

    function formatTarget(signal) {
      return signal.intent && signal.intent.target !== null && signal.intent.target !== undefined
        ? formatNumber(signal.intent.target)
        : "none";
    }

    function formatTimestamp(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }
      return date.toLocaleString();
    }

    function formatAge(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return "unknown age";
      }

      const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
      if (seconds < 15) {
        return "just now";
      }
      if (seconds < 60) {
        return `${seconds}s ago`;
      }

      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) {
        return `${minutes}m ago`;
      }

      const hours = Math.floor(minutes / 60);
      if (hours < 24) {
        return `${hours}h ago`;
      }

      const days = Math.floor(hours / 24);
      return `${days}d ago`;
    }

    function actionClass(action) {
      return `action-${String(action || "wait").toLowerCase()}`;
    }

    function confidenceClass(confidence) {
      if (confidence >= 75) {
        return "confidence-high";
      }
      if (confidence >= 50) {
        return "confidence-medium";
      }
      return "confidence-low";
    }

    function formatMagnet(magnet) {
      if (!magnet) {
        return "none";
      }
      return `${magnet.name} ${formatNumber(magnet.price)}`;
    }

    function formatMidFlow(midTargets) {
      if (!midTargets || !midTargets.flow) {
        return "no_mid_flow";
      }
      return midTargets.flow;
    }

    function formatMidPointName(midPoint) {
      if (!midPoint || !midPoint.name) {
        return "No valid mid";
      }
      return midPoint.name;
    }

    function formatMidPointPrice(midPoint) {
      if (!midPoint || midPoint.price === null || midPoint.price === undefined) {
        return "No valid mid";
      }
      return formatNumber(midPoint.price);
    }

    function formatMagnetPath(magnetPath) {
      if (!Array.isArray(magnetPath) || !magnetPath.length) {
        return '<span class="path-empty">No ranked path available yet.</span>';
      }

      return magnetPath.slice(0, 4).map((magnet, index, list) => {
        const pill = `
          <span class="path-pill">
            <span class="path-rank">#${index + 1}</span>
            <span>${magnet.name} ${formatNumber(magnet.price)}</span>
          </span>
        `;

        if (index === list.length - 1) {
          return pill;
        }

        return `${pill}<span class="path-arrow">→</span>`;
      }).join("");
    }

    function renderPerformance(summary, symbol, errorMessage) {
      if (errorMessage) {
        performanceNode.className = "card-body empty";
        performanceNode.innerHTML = `
          <strong>Performance unavailable</strong>
          ${errorMessage}
        `;
        return;
      }

      if (!summary || !summary.total_signals) {
        performanceNode.className = "card-body empty";
        performanceNode.innerHTML = `
          <strong>No tracked outcomes yet</strong>
          Performance metrics for ${symbol} will appear once actionable signals are stored and evaluated.
        `;
        return;
      }

      performanceNode.className = "card-body";
      performanceNode.innerHTML = `
        <div class="section-head">
          <h3>Performance Summary</h3>
          <span>${summary.symbol}</span>
        </div>
        <div class="performance-grid">
          <div class="performance-metric">
            <span class="metric-label">Total Signals</span>
            <span class="metric-value">${summary.total_signals}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Open</span>
            <span class="metric-value">${summary.open_signals}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Closed</span>
            <span class="metric-value">${summary.closed_signals}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Target Hit</span>
            <span class="metric-value">${summary.target_hit}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Invalidated</span>
            <span class="metric-value">${summary.invalidated}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Expired</span>
            <span class="metric-value">${summary.expired}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Win Rate</span>
            <span class="metric-value">${formatDecimal(summary.win_rate_pct)}%</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Avg MFE</span>
            <span class="metric-value">${formatDecimal(summary.avg_mfe)}</span>
          </div>
          <div class="performance-metric">
            <span class="metric-label">Avg MAE</span>
            <span class="metric-value">${formatDecimal(summary.avg_mae)}</span>
          </div>
        </div>
        <p class="performance-note">
          Closed outcomes are counted once a target is hit, a setup is invalidated, or the tracking window expires.
        </p>
      `;
    }

    function renderLatest(signal) {
      if (!signal) {
        latestNode.className = "card-body empty";
        latestNode.innerHTML = `
          <strong>No signals yet</strong>
          Start the runner and store a signal to populate the live dashboard.
        `;
        return;
      }

      latestNode.className = "card-body";
      latestNode.innerHTML = `
        <div class="topline">
          <span class="pill">${signal.symbol}</span>
          <div class="toolbar-group">
            <span class="pill bias-badge">${signal.resolved_bias}</span>
            <span class="pill confidence-badge ${confidenceClass(signal.confidence)}">Confidence ${signal.confidence}</span>
            <span class="pill action-badge ${actionClass(signal.intent.action)}">${signal.intent.action}</span>
          </div>
        </div>
        <div class="headline">
          <h2>${signal.event_type}</h2>
          <p>
            Latest signal age:
            <span class="signal-age">${formatAge(signal.created_at)}</span>
            | Created ${formatTimestamp(signal.created_at)}
          </p>
        </div>
        <div class="metrics">
          <div class="metric">
            <span class="metric-label">Current Price</span>
            <span class="metric-value">${formatNumber(signal.current_price)}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Action</span>
            <span class="metric-value ${actionClass(signal.intent.action)}">${signal.intent.action}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Target</span>
            <span class="metric-value">${formatTarget(signal)}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Confidence</span>
            <span class="metric-value ${confidenceClass(signal.confidence)}">${signal.confidence}</span>
          </div>
        </div>
        <div class="details-grid">
          <div class="detail-card">
            <span class="detail-label">Resolved Bias</span>
            <span class="detail-value ${actionClass(signal.intent.action)}">${signal.resolved_bias}</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">Anchor Type</span>
            <span class="detail-value">${signal.anchor_type || "none"}</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">ADR State</span>
            <span class="detail-value">${signal.adr_state || "none"}</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">Nearest Magnet</span>
            <span class="detail-value">${formatMagnet(signal.nearest_magnet)}</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">Major Magnet</span>
            <span class="detail-value">${formatMagnet(signal.major_magnet)}</span>
          </div>
          <div class="detail-card">
            <span class="detail-label">Reason</span>
            <span class="detail-value">${signal.intent.reason}</span>
          </div>
        </div>
        <div class="context-block">
          <div class="mid-grid">
            <div class="context-card">
              <span class="detail-label">Mid Flow</span>
              <span class="detail-value">${formatMidFlow(signal.mid_targets)}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Current Mid</span>
              <span class="detail-value">${formatMidPointName(signal.mid_targets && signal.mid_targets.current_mid)}</span>
              <span class="detail-subvalue">Price ${formatMidPointPrice(signal.mid_targets && signal.mid_targets.current_mid)}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Next Mid</span>
              <span class="detail-value">${formatMidPointName(signal.mid_targets && signal.mid_targets.next_mid)}</span>
              <span class="detail-subvalue">Price ${formatMidPointPrice(signal.mid_targets && signal.mid_targets.next_mid)}</span>
            </div>
          </div>
          <div class="context-grid">
            <div class="context-card">
              <span class="detail-label">Structure Type</span>
              <span class="detail-value">${signal.structure && signal.structure.type ? signal.structure.type : "none"}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Structure Direction</span>
              <span class="detail-value">${signal.structure && signal.structure.direction ? signal.structure.direction : "neutral"}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Sweep Type</span>
              <span class="detail-value">${signal.sweep && signal.sweep.type ? signal.sweep.type : "none"}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Sweep Strength</span>
              <span class="detail-value">${signal.sweep ? formatDecimal(signal.sweep.strength) : "0.00"}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Momentum Class</span>
              <span class="detail-value">${signal.momentum && signal.momentum.classification ? signal.momentum.classification : "none"}</span>
            </div>
            <div class="context-card">
              <span class="detail-label">Momentum Direction</span>
              <span class="detail-value">${signal.momentum && signal.momentum.direction ? signal.momentum.direction : "neutral"}</span>
            </div>
          </div>
          <div class="path-summary">
            <span class="detail-label">Magnet Path</span>
            <div class="path-list">${formatMagnetPath(signal.magnet_path)}</div>
          </div>
        </div>
      `;
    }

    function renderRecent(signals) {
      recentCountNode.textContent = `${signals.length} signal${signals.length === 1 ? "" : "s"}`;

      if (!signals.length) {
        recentNode.innerHTML = `
          <div class="empty">
            <strong>History is empty</strong>
            Recent signals will appear here automatically once the engine has activity.
          </div>
        `;
        return;
      }

      recentNode.innerHTML = signals.map((signal) => `
        <section class="signal-item">
          <div class="signal-main">
            <div class="signal-title">
              <strong>${signal.symbol}</strong>
              <span class="pill ${actionClass(signal.intent.action)}">${signal.intent.action}</span>
              <span class="pill">${signal.resolved_bias}</span>
            </div>
            <div>${signal.event_type}</div>
            <div class="status">Age ${formatAge(signal.created_at)} | ${formatTimestamp(signal.created_at)}</div>
          </div>
          <div class="signal-meta">
            <div class="signal-meta-grid">
              <span>Price: ${formatNumber(signal.current_price)}</span>
              <span>Target: ${formatTarget(signal)}</span>
              <span class="${confidenceClass(signal.confidence)}">Confidence: ${signal.confidence}</span>
              <span>Anchor: ${signal.anchor_type || "none"}</span>
            </div>
          </div>
        </section>
      `).join("");
    }

    async function loadSignals() {
      const symbol = symbolInput.value.trim() || "XAUUSD";
      statusNode.textContent = `Loading ${symbol}...`;

      try {
        const [signalsResult, performanceResult] = await Promise.allSettled([
          fetch(`/signals/latest?symbol=${encodeURIComponent(symbol)}&limit=8`),
          fetch(`/performance/summary?symbol=${encodeURIComponent(symbol)}`),
        ]);

        if (signalsResult.status !== "fulfilled") {
          throw signalsResult.reason;
        }

        const signalsResponse = signalsResult.value;
        if (!signalsResponse.ok) {
          throw new Error(`HTTP ${signalsResponse.status}`);
        }

        const payload = await signalsResponse.json();
        const [latest, ...recent] = payload.items || [];
        renderLatest(latest);
        renderRecent(recent);

        let performanceUnavailable = false;
        if (performanceResult.status === "fulfilled") {
          const performanceResponse = performanceResult.value;
          if (performanceResponse.ok) {
            const summary = await performanceResponse.json();
            renderPerformance(summary, payload.symbol, "");
          } else {
            performanceUnavailable = true;
            renderPerformance(null, payload.symbol, `Performance summary request failed with HTTP ${performanceResponse.status}.`);
          }
        } else {
          performanceUnavailable = true;
          renderPerformance(null, payload.symbol, "Performance summary is temporarily unavailable.");
        }

        statusNode.textContent = `Loaded ${payload.count} signal${payload.count === 1 ? "" : "s"} for ${payload.symbol}${performanceUnavailable ? " | Performance unavailable" : ""} | Auto-refresh every 15s`;
      } catch (error) {
        const errorMessage = error && error.message ? error.message : "Unknown error";
        latestNode.className = "card-body empty";
        latestNode.innerHTML = `
          <strong>Dashboard refresh failed</strong>
          ${errorMessage}
        `;
        renderPerformance(null, symbol, "Performance summary is unavailable until the dashboard can reach the API.");
        recentNode.innerHTML = "";
        recentCountNode.textContent = "0 signals";
        statusNode.textContent = "Dashboard refresh failed";
      }
    }

    refreshButton.addEventListener("click", loadSignals);
    symbolInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        loadSignals();
      }
    });

    loadSignals();
    window.setInterval(loadSignals, 15000);
  </script>
</body>
</html>
        """
    )
