def build_landing_page_html() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ObserverAI Magnet Engine</title>
  <style>
    :root {
      --bg: #f4efe6;
      --panel: #fffdf8;
      --panel-soft: #f8f1e6;
      --ink: #1f1d1a;
      --muted: #6a645d;
      --line: #d8cfc0;
      --accent: #8b5e34;
      --accent-strong: #6f4826;
      --buy: #1d6b45;
      --shadow: 0 24px 56px rgba(71, 51, 27, 0.1);
      --shadow-soft: 0 10px 24px rgba(71, 51, 27, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(139, 94, 52, 0.16), transparent 28%),
        linear-gradient(180deg, #fbf7f1 0%, var(--bg) 100%);
      min-height: 100vh;
    }

    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 56px;
    }

    .nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 28px;
      padding: 14px 18px;
      border: 1px solid rgba(216, 207, 192, 0.9);
      border-radius: 20px;
      background: rgba(255, 253, 248, 0.88);
      box-shadow: var(--shadow-soft);
      backdrop-filter: blur(10px);
    }

    .brand {
      display: grid;
      gap: 3px;
    }

    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    .brand strong {
      font-size: 18px;
    }

    .nav-links {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 14px;
      color: var(--muted);
    }

    .nav-links a {
      color: inherit;
      text-decoration: none;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.85fr);
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }

    .hero-card,
    .panel {
      background: var(--panel);
      border: 1px solid rgba(216, 207, 192, 0.94);
      border-radius: 28px;
      box-shadow: var(--shadow);
    }

    .hero-card {
      position: relative;
      overflow: hidden;
      padding: 34px;
      background:
        linear-gradient(145deg, rgba(248, 241, 230, 0.98), rgba(255, 253, 248, 0.98)),
        var(--panel);
    }

    .hero-card::after {
      content: "";
      position: absolute;
      right: -52px;
      bottom: -52px;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(139, 94, 52, 0.18), transparent 68%);
      pointer-events: none;
    }

    .hero-copy {
      position: relative;
      z-index: 1;
      display: grid;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: clamp(42px, 6vw, 72px);
      line-height: 0.94;
      font-weight: 600;
      max-width: 720px;
    }

    .hero-copy p {
      margin: 0;
      max-width: 700px;
      font-size: 18px;
      line-height: 1.6;
      color: var(--muted);
    }

    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-top: 8px;
    }

    .button {
      border: 0;
      border-radius: 999px;
      padding: 14px 20px;
      font: inherit;
      cursor: pointer;
      text-decoration: none;
      transition: transform 140ms ease, opacity 140ms ease;
    }

    .button:hover {
      opacity: 0.94;
      transform: translateY(-1px);
    }

    .button-primary {
      background: var(--accent-strong);
      color: #fff;
      box-shadow: var(--shadow-soft);
    }

    .button-secondary {
      background: var(--panel-soft);
      color: var(--accent);
      border: 1px solid rgba(216, 207, 192, 0.9);
    }

    .hero-note {
      font-size: 14px;
      color: var(--muted);
    }

    .status {
      min-height: 22px;
      font-size: 14px;
      color: var(--muted);
    }

    .status.error {
      color: #9f3427;
    }

    .status.success {
      color: var(--buy);
    }

    .hero-side {
      display: grid;
      gap: 16px;
      padding: 24px;
    }

    .hero-side h2 {
      margin: 0;
      font-size: 24px;
    }

    .hero-side p,
    .hero-side li {
      color: var(--muted);
      line-height: 1.55;
      font-size: 15px;
    }

    .hero-side ul {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }

    .section-grid {
      display: grid;
      gap: 20px;
      margin-top: 20px;
    }

    .two-up {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 20px;
    }

    .panel {
      padding: 24px;
    }

    .panel h3 {
      margin: 0 0 12px;
      font-size: 28px;
    }

    .panel p {
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 16px;
    }

    .feature-grid,
    .step-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }

    .feature,
    .step {
      padding: 18px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(216, 207, 192, 0.84);
    }

    .feature strong,
    .step strong {
      display: block;
      margin-bottom: 8px;
      font-size: 17px;
    }

    .pricing-card {
      display: grid;
      gap: 14px;
      align-content: start;
      background:
        linear-gradient(180deg, rgba(248, 241, 230, 0.98), rgba(255, 253, 248, 0.98)),
        var(--panel);
    }

    .price-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      border-radius: 999px;
      padding: 8px 12px;
      border: 1px solid rgba(216, 207, 192, 0.9);
      background: var(--panel-soft);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .pricing-list {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 10px;
      color: var(--muted);
      line-height: 1.55;
    }

    .cta-panel {
      display: grid;
      gap: 12px;
      align-items: center;
      justify-items: start;
      text-align: left;
    }

    code {
      font-family: Consolas, "Courier New", monospace;
      background: rgba(248, 241, 230, 0.9);
      padding: 2px 6px;
      border-radius: 8px;
      font-size: 0.95em;
    }

    @media (max-width: 920px) {
      .hero,
      .two-up,
      .feature-grid,
      .step-grid {
        grid-template-columns: 1fr;
      }

      h1 {
        font-size: clamp(38px, 10vw, 62px);
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <nav class="nav">
      <div class="brand">
        <span class="eyebrow">ObserverAI Magnet Engine</span>
        <strong>Production-grade XAUUSD signal infrastructure</strong>
      </div>
      <div class="nav-links">
        <a href="#features">Features</a>
        <a href="#how-it-works">How It Works</a>
        <a href="#pricing">Pricing</a>
        <a href="/dashboard">Dashboard</a>
      </div>
    </nav>

    <section class="hero">
      <article class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">Real-Time Gold Workflow</span>
          <h1>Run London-session XAUUSD signal generation without stitching the backend together by hand.</h1>
          <p>
            ObserverAI Magnet Engine turns MT5 market data into evaluated signals, persistent history, outcome tracking,
            dashboard visibility, and alert delivery so you can focus on strategy quality instead of backend plumbing.
          </p>
          <div class="hero-actions">
            <button
              id="start-pro-button"
              class="button button-primary checkout-button"
              type="button"
              data-price-id="price_your_pro_plan"
            >
              Start with Pro
            </button>
            <a class="button button-secondary" href="/dashboard">View Live Dashboard</a>
          </div>
          <div class="hero-note">
            Built for FastAPI, MT5 ingestion, real-time evaluation, Telegram alerts, and signal performance tracking.
          </div>
          <div id="checkout-status" class="status"></div>
        </div>
      </article>

      <aside class="hero-card hero-side">
        <h2>What Pro unlocks first</h2>
        <ul>
          <li>Live MT5 polling and oracle evaluation for XAUUSD M15.</li>
          <li>Persisted signals, intent, deduplicated Telegram delivery, and outcome tracking.</li>
          <li>Same-origin dashboard visibility for latest signals, history, and performance summary.</li>
        </ul>
        <p>
          The first checkout button is wired to Stripe Checkout in subscription mode, ready for your live
          Stripe Price ID.
        </p>
      </aside>
    </section>

    <section id="features" class="section-grid">
      <article class="panel">
        <span class="eyebrow">Features</span>
        <h3>Everything needed to move from demo evaluation to monitored signal ops.</h3>
        <div class="feature-grid">
          <div class="feature">
            <strong>Signal Engine</strong>
            Anchor, ADR, levels, magnets, event resolution, intent, and confidence work together in one evaluation flow.
          </div>
          <div class="feature">
            <strong>Live Delivery</strong>
            MT5 data ingestion, persisted signals, Telegram alerting, and dashboard consumption stay on the same backend.
          </div>
          <div class="feature">
            <strong>Performance Tracking</strong>
            Open outcomes, target hits, invalidations, expiry, MFE, and MAE give you a measurable feedback loop.
          </div>
        </div>
      </article>
    </section>

    <section class="two-up">
      <article id="how-it-works" class="panel">
        <span class="eyebrow">How It Works</span>
        <h3>Go from MT5 candles to a stored, monitored trading intent.</h3>
        <div class="step-grid">
          <div class="step">
            <strong>1. Ingest</strong>
            The runner collects M1, M15, and daily candles, current price, previous M15 close, and ATR from MT5.
          </div>
          <div class="step">
            <strong>2. Evaluate</strong>
            The oracle resolves structure, bias, event direction, magnets, intent, and confidence for the current setup.
          </div>
          <div class="step">
            <strong>3. Monitor</strong>
            Signals are stored, outcomes are tracked, and the dashboard surfaces both the latest setup and performance health.
          </div>
        </div>
      </article>

      <article id="pricing" class="panel pricing-card">
        <span class="price-badge">Pricing Teaser</span>
        <h3>Start with Pro and keep the stack focused.</h3>
        <p>
          Pro is the simple starting point for teams that want one subscription-ready backend for live signal generation,
          alert delivery, persistence, and operator visibility.
        </p>
        <ul class="pricing-list">
          <li>One Stripe Checkout subscription flow wired from the landing page.</li>
          <li>One live monitoring surface for signals and performance.</li>
          <li>One clean backend path from MT5 data to actionable intent.</li>
        </ul>
        <button
          class="button button-primary checkout-button"
          type="button"
          data-price-id="price_your_pro_plan"
        >
          Start with Pro
        </button>
      </article>
    </section>

    <section class="section-grid">
      <article class="panel cta-panel">
        <span class="eyebrow">CTA</span>
        <h3>Connect your Stripe Price ID, launch checkout, and put the first paid path in front of users.</h3>
        <p>
          Keep the app structure intact, keep checkout minimal, and use this first Stripe button as the clean handoff
          from landing page interest to subscription onboarding.
        </p>
      </article>
    </section>
  </main>

  <script>
    const checkoutButtons = Array.from(document.querySelectorAll(".checkout-button"));
    const checkoutStatus = document.getElementById("checkout-status");

    function setStatus(message, tone) {
      checkoutStatus.textContent = message;
      checkoutStatus.className = `status${tone ? ` ${tone}` : ""}`;
    }

    async function startCheckout(button) {
      const priceId = button.dataset.priceId || "";
      if (!priceId) {
        setStatus("Stripe Price ID is missing from the Start with Pro button.", "error");
        return;
      }

      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = "Starting checkout...";
      setStatus("Creating Stripe Checkout session...", "");

      try {
        const response = await fetch("/billing/create-checkout-session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ price_id: priceId }),
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || `HTTP ${response.status}`);
        }

        if (!payload.url) {
          throw new Error("Stripe Checkout URL missing from response.");
        }

        setStatus("Redirecting to Stripe Checkout...", "success");
        window.location.assign(payload.url);
      } catch (error) {
        const message = error && error.message ? error.message : "Checkout could not be started.";
        setStatus(message, "error");
        button.disabled = false;
        button.textContent = originalLabel;
      }
    }

    checkoutButtons.forEach((button) => {
      button.addEventListener("click", () => startCheckout(button));
    });
  </script>
</body>
</html>
"""
