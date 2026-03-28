import { useEffect, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function safeParseJson(rawBody) {
  if (!rawBody) {
    return null;
  }

  try {
    return JSON.parse(rawBody);
  } catch {
    return null;
  }
}

async function fetchJson(path, signal) {
  const requestPath = API_BASE_URL ? `${API_BASE_URL}${path}` : path;
  let response = await fetch(requestPath, { signal });
  let rawBody = await response.text();
  let payload = safeParseJson(rawBody);

  if (!response.ok && response.status === 404 && path.startsWith("/api/")) {
    const fallbackPath = path.replace(/^\/api/, "");
    const fallbackRequestPath = API_BASE_URL
      ? `${API_BASE_URL}${fallbackPath}`
      : fallbackPath;

    response = await fetch(fallbackRequestPath, { signal });
    rawBody = await response.text();
    payload = safeParseJson(rawBody);
  }

  if (!response.ok) {
    throw new Error(payload?.detail || "Backend request failed.");
  }

  return payload ?? {};
}

function formatCurrency(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "Unavailable";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return `${value.toFixed(1)}%`;
}

function formatTradeCount(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return Math.round(value).toString();
}

function normalizeHistory(response) {
  if (!response || !Array.isArray(response.history)) {
    return [];
  }

  return response.history.slice(-5).reverse();
}

function App() {
  const [dashboard, setDashboard] = useState({
    price: null,
    prediction: null,
    sentiment: null,
    history: [],
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const hasDashboardData =
    dashboard.price !== null ||
    dashboard.sentiment !== null ||
    dashboard.prediction !== null ||
    dashboard.history.length > 0;

  useEffect(() => {
    const abortController = new AbortController();

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const [priceResult, predictionResult, sentimentResult, historyResult] = await Promise.allSettled([
          fetchJson("/api/price", abortController.signal),
          fetchJson("/api/predict", abortController.signal),
          fetchJson("/api/sentiment", abortController.signal),
          fetchJson("/api/history", abortController.signal),
        ]);

        const price =
          priceResult.status === "fulfilled" ? priceResult.value : null;
        const prediction =
          predictionResult.status === "fulfilled" ? predictionResult.value : null;
        const sentiment =
          sentimentResult.status === "fulfilled" ? sentimentResult.value : null;
        const historyResponse =
          historyResult.status === "fulfilled" ? historyResult.value : null;

        const wasAborted =
          abortController.signal.aborted ||
          [priceResult, predictionResult, sentimentResult, historyResult].some(
            (result) =>
              result.status === "rejected" &&
              result.reason?.name === "AbortError",
          );

        if (wasAborted) {
          return;
        }

        if (
          priceResult.status === "rejected" &&
          predictionResult.status === "rejected" &&
          sentimentResult.status === "rejected" &&
          historyResult.status === "rejected"
        ) {
          throw new Error("Backend request failed.");
        }

        setDashboard({
          price: price ?? null,
          prediction: prediction ?? null,
          sentiment: sentiment ?? prediction?.sentiment ?? null,
          history: normalizeHistory(historyResponse),
        });
      } catch (err) {
        if (err.name !== "AbortError" && !abortController.signal.aborted) {
          setError(err.message || "Unable to load GoldHelm AI market data.");
        }
      } finally {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => abortController.abort();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-brand">
          <img
            className="hero-logo"
            src="/goldhelm-logo.png"
            alt="GoldHelm AI logo"
          />
          <div className="hero-copy">
            <p className="eyebrow">GoldHelm AI</p>
            <h1>Gold intelligence with explainable next-day forecasts.</h1>
            <p className="hero-text">
              Track the latest futures close, view recent history, and inspect the
              model&apos;s next-session prediction with validation context.
            </p>
          </div>
        </div>
      </section>

      {loading && <p className="status">Loading market data...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && hasDashboardData && (
        <>
          <section className="cards">
            <article className="card primary-card">
              <p className="card-label">Current Close</p>
              <h2>{formatCurrency(dashboard.price?.price)}</h2>
              <p className="card-meta">
                {dashboard.price?.ticker} as of {dashboard.price?.date}
              </p>
            </article>

            <article className="card">
              <p className="card-label">Next-Day Forecast</p>
              <h2>{formatCurrency(dashboard.prediction?.prediction)}</h2>
              <p className="card-meta">
                Current: {formatCurrency(dashboard.prediction?.current_price || dashboard.price?.price)}
              </p>
              <p className="card-meta">
                Expected move: {dashboard.prediction?.predicted_change_pct?.toFixed(3)}%
              </p>
            </article>

            <article className="card">
              <p className="card-label">Model Quality</p>
              <h2>{formatPercent((dashboard.prediction?.confidence ?? NaN) * 100)}</h2>
              <p className="card-meta">
                Validation MAE: {formatCurrency(dashboard.prediction?.validation_mae)}
              </p>
            </article>

            <article className="card">
              <p className="card-label">Market Sentiment</p>
              <h2 className="sentiment-label">
                {dashboard.sentiment?.label || dashboard.prediction?.sentiment?.label || "Neutral"}
              </h2>
              <p className="card-meta">
                Score:{" "}
                {typeof (dashboard.sentiment?.score ?? dashboard.prediction?.sentiment?.score) ===
                "number"
                  ? (dashboard.sentiment?.score ?? dashboard.prediction?.sentiment?.score).toFixed(3)
                  : "N/A"}
              </p>
            </article>

            <article className="card decision-card">
              <p className="card-label">Final Decision</p>
              <h2 className="decision-label">
                {dashboard.prediction?.decision || "HOLD"}
              </h2>
              <p className="card-meta">
                Combined confidence: {formatPercent((dashboard.prediction?.confidence ?? NaN) * 100)}
              </p>
              <p className="card-meta">
                RL suggestion: {dashboard.prediction?.rl_decision || "Unavailable"}
              </p>
            </article>
          </section>

          <section className="insight-panel">
            <div className="section-heading">
              <h3>Final Analysis</h3>
              <p>Coordinator output combining reasoning and reinforcement learning signals.</p>
            </div>

            <div className="explanation-list">
              {(dashboard.prediction?.final_analysis ?? []).length > 0 ? (
                dashboard.prediction.final_analysis.map((reason) => (
                  <article className="explanation-row" key={reason}>
                    {reason}
                  </article>
                ))
              ) : (
                <article className="explanation-row">
                  Final analysis will appear when the prediction endpoint provides it.
                </article>
              )}
            </div>
          </section>

          <section className="debate-panel">
            <div className="section-heading">
              <h3>Agent Debate</h3>
              <p>Reasoning agent and RL policy compared before the final decision is set.</p>
            </div>

            <div className="debate-grid">
              <article className="debate-card">
                <p className="card-label">Reasoning Agent</p>
                <h4>{dashboard.prediction?.debate?.reasoning_agent?.decision || "N/A"}</h4>
                <p className="card-meta">
                  Confidence: {formatPercent((dashboard.prediction?.debate?.reasoning_agent?.confidence ?? NaN) * 100)}
                </p>
              </article>

              <article className="debate-card">
                <p className="card-label">RL Agent</p>
                <h4>{dashboard.prediction?.debate?.rl_agent?.decision || "N/A"}</h4>
                <p className="card-meta">
                  Confidence: {formatPercent((dashboard.prediction?.debate?.rl_agent?.confidence ?? NaN) * 100)}
                </p>
                <p className="card-meta">
                  Policy: {dashboard.prediction?.debate?.policy_source || "Unavailable"}
                </p>
              </article>

              <article className="debate-card">
                <p className="card-label">Agreement</p>
                <h4>{dashboard.prediction?.debate?.agreement ? "Aligned" : "Mixed"}</h4>
                <p className="card-meta">
                  Coordinator resolves disagreements by defaulting to caution.
                </p>
              </article>
            </div>
          </section>

          <section className="backtest-panel">
            <div className="section-heading">
              <h3>RL Backtest</h3>
              <p>Offline policy evaluation from the trained trading environment.</p>
            </div>

            <div className="backtest-grid">
              <article className="backtest-card">
                <p className="card-label">Total Return</p>
                <h4>{formatPercent((dashboard.prediction?.backtest?.total_return ?? NaN) * 100)}</h4>
              </article>
              <article className="backtest-card">
                <p className="card-label">Trades</p>
                <h4>{formatTradeCount(dashboard.prediction?.backtest?.number_of_trades)}</h4>
              </article>
              <article className="backtest-card">
                <p className="card-label">Win Rate</p>
                <h4>{formatPercent((dashboard.prediction?.backtest?.win_rate ?? NaN) * 100)}</h4>
              </article>
              <article className="backtest-card">
                <p className="card-label">Final Portfolio</p>
                <h4>{formatCurrency(dashboard.prediction?.backtest?.final_portfolio_value)}</h4>
              </article>
            </div>
          </section>

          <section className="history-panel">
            <div className="section-heading">
              <h3>Recent closes</h3>
              <p>Latest five trading sessions from the backend history feed.</p>
            </div>

            <div className="history-list">
              {dashboard.history.length > 0 ? (
                dashboard.history.map((item) => (
                  <article className="history-row" key={item.date}>
                    <span>{item.date}</span>
                    <strong>{formatCurrency(item.close)}</strong>
                  </article>
                ))
              ) : (
                <article className="history-row">
                  <span>History unavailable</span>
                  <strong>Retrying backend feed</strong>
                </article>
              )}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export default App;
