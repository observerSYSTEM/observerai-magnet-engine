"use client";

import { useMemo, useState } from "react";

import styles from "./page.module.css";

type CheckoutState = {
  tone: "idle" | "success" | "error";
  message: string;
};

type CreateCheckoutSessionResponse = {
  url: string;
};

const PRO_PRICE_ID = "price_1TOJizJnivDywsdRuatzdkRC";

const TRUST_ITEMS = [
  "Live MT5 input",
  "Bias + magnet logic",
  "Telegram-ready alerts",
  "Outcome tracking",
];

const FEATURES = [
  {
    title: "Structured Signals",
    description:
      "Bias, targets, magnets, and trade intent are resolved into a clean signal view that is easy to act on.",
  },
  {
    title: "Liquidity Magnets",
    description:
      "Signals stay grounded in visible draws and session structure rather than one-dimensional direction calls.",
  },
  {
    title: "Telegram Delivery",
    description:
      "Alerts are delivered in a concise, trader-friendly format that keeps the context readable in real time.",
  },
  {
    title: "Performance Tracking",
    description:
      "Every stored signal can be reviewed against outcomes, follow-through, and overall strategy performance.",
  },
];

const STEPS = [
  {
    title: "Ingest market data",
    description:
      "Pull live MT5 candles, price, and volatility into one evaluation flow.",
  },
  {
    title: "Evaluate context",
    description:
      "Resolve structure, bias, magnets, targets, and confidence in a single pass.",
  },
  {
    title: "Deliver signal",
    description:
      "Publish the signal to the dashboard and Telegram without extra manual steps.",
  },
  {
    title: "Track outcome",
    description:
      "Store the result so signal quality can be reviewed over time.",
  },
];

const PRICING = [
  {
    name: "Pro",
    badge: "Available now",
    description:
      "Real-time signal generation, dashboard access, Telegram delivery, and measurable outcome tracking.",
    bullets: [
      "Real-time XAUUSD signal evaluation",
      "Live dashboard access",
      "Telegram delivery",
      "Outcome and performance tracking",
    ],
  },
  {
    name: "Elite",
    badge: "Coming soon",
    description:
      "Expanded coverage, deeper filtering, and a broader operating view for more advanced workflows.",
    bullets: [
      "Advanced signal filtering",
      "Multi-symbol support",
      "Deeper analytics",
      "Expanded review tooling",
    ],
  },
];

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
}

function getDashboardHref(apiBaseUrl: string): string {
  return apiBaseUrl ? `${apiBaseUrl}/dashboard` : "/dashboard";
}

function getCheckoutEndpoint(apiBaseUrl: string): string {
  return apiBaseUrl
    ? `${apiBaseUrl}/billing/create-checkout-session`
    : "/billing/create-checkout-session";
}

export default function HomePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [checkoutState, setCheckoutState] = useState<CheckoutState>({
    tone: "idle",
    message: "",
  });

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const dashboardHref = useMemo(() => getDashboardHref(apiBaseUrl), [apiBaseUrl]);

  async function handleStartPro() {
    setIsLoading(true);
    setCheckoutState({
      tone: "idle",
      message: "Creating your Stripe Checkout session...",
    });

    try {
      const response = await fetch(getCheckoutEndpoint(apiBaseUrl), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ price_id: PRO_PRICE_ID }),
      });

      const payload = (await response.json()) as Partial<CreateCheckoutSessionResponse> & {
        detail?: string;
      };

      if (!response.ok) {
        throw new Error(payload.detail || `Checkout failed with HTTP ${response.status}.`);
      }

      if (!payload.url) {
        throw new Error("Stripe Checkout URL was missing from the backend response.");
      }

      setCheckoutState({
        tone: "success",
        message: "Redirecting to Stripe Checkout...",
      });
      window.location.assign(payload.url);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Checkout could not be started. Please try again.";
      setCheckoutState({
        tone: "error",
        message,
      });
      setIsLoading(false);
    }
  }

  const statusClassName =
    checkoutState.tone === "error"
      ? `${styles.status} ${styles.statusError}`
      : checkoutState.tone === "success"
        ? `${styles.status} ${styles.statusSuccess}`
        : styles.status;

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <nav className={styles.nav}>
          <span className={styles.brand}>ObserverAI Magnet Engine</span>
          <div className={styles.navLinks}>
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href={dashboardHref}>Dashboard</a>
          </div>
        </nav>

        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <span className={styles.eyebrow}>Structured Trading Intelligence</span>
            <h1 className={styles.heroTitle}>
              High-context XAUUSD signals, delivered with structure.
            </h1>
            <p className={styles.heroLead}>
              ObserverAI turns live market data into structured trading alerts
              with bias, magnets, targets, and performance tracking.
            </p>
            <div className={styles.buttonRow}>
              <button
                className={`${styles.primaryButton} ${
                  isLoading ? styles.buttonDisabled : ""
                }`}
                type="button"
                onClick={handleStartPro}
                disabled={isLoading}
              >
                {isLoading ? "Starting Checkout..." : "Start with Pro"}
              </button>
              <a className={styles.secondaryButton} href={dashboardHref}>
                View Live Dashboard
              </a>
            </div>
            <div className={styles.checkoutMeta}>
              <div className={statusClassName}>{checkoutState.message}</div>
            </div>
          </div>

          <aside className={styles.heroPanel}>
            <span className={styles.panelLabel}>Operator View</span>
            <div className={styles.panelRows}>
              <div className={styles.panelRow}>
                <span>Market</span>
                <strong>XAUUSD / M15</strong>
              </div>
              <div className={styles.panelRow}>
                <span>Signal Output</span>
                <strong>Bias, magnets, target</strong>
              </div>
              <div className={styles.panelRow}>
                <span>Delivery</span>
                <strong>Dashboard + Telegram</strong>
              </div>
              <div className={styles.panelRow}>
                <span>Review</span>
                <strong>Outcome tracking</strong>
              </div>
            </div>
            <p className={styles.panelNote}>
              Built for traders who want the alert to arrive with enough context
              to be useful, not noisy.
            </p>
          </aside>
        </section>

        <section className={styles.trustStrip} aria-label="Trust strip">
          {TRUST_ITEMS.map((item) => (
            <div key={item} className={styles.trustItem}>
              <span className={styles.trustDot} aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
        </section>

        <section id="features" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>Features</span>
            <h2>Focused tooling for signal clarity.</h2>
            <p>
              The product stays intentionally compact: clear evaluation,
              readable delivery, and measurable follow-through.
            </p>
          </div>
          <div className={styles.featureGrid}>
            {FEATURES.map((feature) => (
              <article key={feature.title} className={styles.card}>
                <span className={styles.cardLabel}>Core Layer</span>
                <h3 className={styles.cardTitle}>{feature.title}</h3>
                <p className={styles.cardBody}>{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>How It Works</span>
            <h2>A simple flow from input to review.</h2>
          </div>
          <div className={styles.stepGrid}>
            {STEPS.map((step, index) => (
              <article key={step.title} className={styles.stepCard}>
                <span className={styles.stepNumber}>0{index + 1}</span>
                <h3 className={styles.cardTitle}>{step.title}</h3>
                <p className={styles.cardBody}>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="pricing" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>Pricing</span>
            <h2>Choose the operating tier that fits now.</h2>
            <p>
              Start with Pro for live delivery and tracking. Elite expands the
              workflow when broader coverage is needed.
            </p>
          </div>
          <div className={styles.pricingGrid}>
            {PRICING.map((tier) => (
              <article
                key={tier.name}
                className={`${styles.card} ${styles.pricingCard} ${
                  tier.name === "Pro" ? styles.pricingFeatured : ""
                }`}
              >
                <div className={styles.pricingHeader}>
                  <div className={styles.pricingTitleGroup}>
                    <h3 className={styles.cardTitle}>{tier.name}</h3>
                    <p className={styles.cardBody}>{tier.description}</p>
                  </div>
                  <span className={styles.badge}>{tier.badge}</span>
                </div>
                <ul className={styles.pricingList}>
                  {tier.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
                {tier.name === "Pro" ? (
                  <button
                    className={`${styles.primaryButton} ${
                      isLoading ? styles.buttonDisabled : ""
                    }`}
                    type="button"
                    onClick={handleStartPro}
                    disabled={isLoading}
                  >
                    {isLoading ? "Starting Checkout..." : "Start with Pro"}
                  </button>
                ) : (
                  <span className={styles.comingSoon}>
                    Elite release in preparation.
                  </span>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <article className={styles.finalCta}>
            <div className={styles.finalCtaCopy}>
              <span className={styles.eyebrow}>Get Started</span>
              <h2>Start tracking structured XAUUSD signals today.</h2>
              <p>
                Keep the workflow simple: evaluate, deliver, and measure signal
                quality in one place.
              </p>
            </div>
            <div className={styles.finalCtaActions}>
              <button
                className={`${styles.primaryButton} ${
                  isLoading ? styles.buttonDisabled : ""
                }`}
                type="button"
                onClick={handleStartPro}
                disabled={isLoading}
              >
                {isLoading ? "Starting Checkout..." : "Start with Pro"}
              </button>
              <a className={styles.secondaryButton} href={dashboardHref}>
                View Live Dashboard
              </a>
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
