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

const FEATURES = [
  {
    title: "Signal intelligence, not random alerts",
    description:
      "Every setup is shaped by London-session structure, liquidity, and momentum so the signal has context before it reaches you.",
  },
  {
    title: "Actionable output",
    description:
      "See the direction, target, and signal intent clearly so decisions feel deliberate instead of rushed.",
  },
  {
    title: "Live delivery",
    description:
      "Move from evaluation to dashboard visibility and Telegram-ready delivery without extra operational glue.",
  },
  {
    title: "Performance tracking built in",
    description:
      "Track open outcomes, target hits, invalidations, and measurable follow-through after the signal is sent.",
  },
];

const STEPS = [
  {
    title: "Ingest",
    description:
      "Pull fresh MT5 market data into a signal engine built specifically for XAUUSD session behavior.",
  },
  {
    title: "Evaluate",
    description:
      "Resolve structure, bias, magnets, intent, and confidence so the output carries reasoning, not just direction.",
  },
  {
    title: "Deliver & Track",
    description:
      "Push the signal into your operator workflow and measure how it performs after it reaches the market.",
  },
];

const PRICING = [
  {
    name: "Pro",
    tag: "Available now",
    description:
      "Real-time signal generation, dashboard access, Telegram delivery, outcome tracking, performance metrics.",
    bullets: [
      "Real-time signal generation",
      "Dashboard access",
      "Telegram delivery",
      "Outcome tracking",
      "Performance metrics",
    ],
  },
  {
    name: "Elite",
    tag: "Coming soon",
    description:
      "Advanced filtering, multi-symbol support, and deeper analytics for traders who want a broader operating view.",
    bullets: [
      "Advanced filtering",
      "Multi-symbol support",
      "Deeper analytics",
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
          <div className={styles.brand}>
            <span className={styles.eyebrow}>ObserverAI Magnet Engine</span>
            <strong className={styles.brandTitle}>
              High-context XAUUSD signal infrastructure
            </strong>
          </div>
          <div className={styles.navLinks}>
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#pricing">Pricing</a>
            <a href={dashboardHref}>Dashboard</a>
          </div>
        </nav>

        <section className={styles.hero}>
          <article className={styles.heroCard}>
            <div className={styles.heroCopy}>
              <span className={styles.eyebrow}>ObserverAI Magnet Engine</span>
              <h1 className={styles.heroTitle}>
                High-context XAUUSD signals with real-time delivery and measurable
                performance.
              </h1>
              <p className={styles.heroLead}>
                Built around London-session structure, liquidity, and momentum,
                so you&apos;re not just getting alerts, you&apos;re getting context,
                targets, and outcomes you can track.
              </p>
              <p className={styles.heroSubcopy}>
                Designed for traders who want signal quality to feel composed,
                operator-ready, and accountable after the alert is sent.
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
                <div className={styles.priceNote}>
                  Stripe note: replace <code>{PRO_PRICE_ID}</code> with your live
                  Stripe Price ID before launch.
                </div>
              </div>
            </div>
          </article>

          <aside className={`${styles.heroCard} ${styles.heroAside}`}>
            <span className={styles.eyebrow}>Premium Positioning</span>
            <h2>Built for traders who prefer clarity over noise.</h2>
            <p>
              ObserverAI Magnet Engine is for desks and independent traders who
              want structure over guesswork, signals backed by logic, and
              performance they can measure over time.
            </p>
            <div className={styles.signalPulse}>
              <div className={styles.signalTagRow}>
                <span className={styles.signalTag}>Context</span>
                <span className={styles.signalTag}>Delivery</span>
                <span className={styles.signalTag}>Performance</span>
              </div>
              <p>
                From live MT5 inputs to a trader-facing output, the experience
                stays focused on what matters: where the signal sits, why it
                matters, and how it performed afterward.
              </p>
            </div>
          </aside>
        </section>

        <section className={styles.trustStrip}>
          <span className={styles.eyebrow}>Trust / Positioning</span>
          <p>
            Designed for traders who want clarity over noise, structure over
            guesswork, signals backed by logic, and performance they can
            measure.
          </p>
        </section>

        <section id="features" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>Features</span>
            <h2>Signal quality that feels composed before it reaches the desk.</h2>
            <p>
              Premium signal tooling should reduce hesitation, not create more
              of it. Each layer is tuned to make the output clearer, more usable,
              and easier to monitor.
            </p>
          </div>
          <div className={styles.featureGrid}>
            {FEATURES.map((feature) => (
              <article key={feature.title} className={styles.card}>
                <h3 className={styles.cardTitle}>{feature.title}</h3>
                <p className={styles.cardBody}>{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>How it works</span>
            <h2>Three steps from market input to accountable signal delivery.</h2>
            <p>
              The workflow is intentionally simple: bring the market in, evaluate
              it with structure, then deliver and track what happened next.
            </p>
          </div>
          <div className={styles.howGrid}>
            {STEPS.map((step, index) => (
              <article key={step.title} className={styles.card}>
                <span className={styles.stepNumber}>{index + 1}</span>
                <h3 className={styles.cardTitle}>{step.title}</h3>
                <p className={styles.cardBody}>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="pricing" className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.eyebrow}>Pricing</span>
            <h2>Start with the tier that gets signals into motion quickly.</h2>
            <p>
              Keep the buying decision clean. Pro is the immediate path. Elite
              expands the operating surface when you want more coverage and
              deeper analysis.
            </p>
          </div>
          <div className={styles.pricingGrid}>
            {PRICING.map((tier) => (
              <article key={tier.name} className={`${styles.card} ${styles.pricingTier}`}>
                <div className={styles.pricingHeader}>
                  <h3 className={styles.cardTitle}>{tier.name}</h3>
                  <span className={styles.tierTag}>{tier.tag}</span>
                </div>
                <p className={styles.cardBody}>{tier.description}</p>
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
                ) : null}
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <article className={`${styles.card} ${styles.finalCta}`}>
            <span className={styles.eyebrow}>Final CTA</span>
            <h2>Start tracking high-context XAUUSD signals today.</h2>
            <p>
              Launch with a clean Pro entry point, keep the offer focused, and
              send traders from premium positioning straight into Stripe Checkout.
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
            <div className={styles.priceNote}>
              Replace <code>{PRO_PRICE_ID}</code> before launch so checkout points
              to the live Stripe subscription price.
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
