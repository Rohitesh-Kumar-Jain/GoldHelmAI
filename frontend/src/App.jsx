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
    history: [],
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const hasDashboardData =
    dashboard.price !== null ||
    dashboard.prediction !== null ||
    dashboard.history.length > 0;

  useEffect(() => {
    const abortController = new AbortController();

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const [priceResult, predictionResult, historyResult] = await Promise.allSettled([
          fetchJson("/api/price", abortController.signal),
          fetchJson("/api/predict", abortController.signal),
          fetchJson("/api/history", abortController.signal),
        ]);

        const price =
          priceResult.status === "fulfilled" ? priceResult.value : null;
        const prediction =
          predictionResult.status === "fulfilled" ? predictionResult.value : null;
        const historyResponse =
          historyResult.status === "fulfilled" ? historyResult.value : null;

        const wasAborted =
          abortController.signal.aborted ||
          [priceResult, predictionResult, historyResult].some(
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
          historyResult.status === "rejected"
        ) {
          throw new Error("Backend request failed.");
        }

        setDashboard({
          price: price ?? null,
          prediction: prediction ?? null,
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
