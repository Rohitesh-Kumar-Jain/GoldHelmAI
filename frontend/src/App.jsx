import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const INDICATOR_ORDER = [
  "rsi",
  "moving_averages",
  "macd",
  "bollinger_bands",
  "momentum",
  "atr",
  "stochastic",
  "obv",
  "fibonacci",
  "adx",
];

const INDICATOR_META = {
  rsi: {
    title: "RSI (14)",
    blurb: "Momentum oscillator showing whether price is stretched to the upside or downside.",
  },
  moving_averages: {
    title: "Moving Averages",
    blurb: "Trend filter comparing the latest close against medium- and long-term average price.",
  },
  macd: {
    title: "MACD",
    blurb: "Trend-following momentum measure comparing fast and slow exponential averages.",
  },
  bollinger_bands: {
    title: "Bollinger Bands",
    blurb: "Volatility envelope showing whether price is pressing near statistical extremes.",
  },
  momentum: {
    title: "Momentum",
    blurb: "Raw price acceleration over the recent lookback window.",
  },
  atr: {
    title: "ATR (14)",
    blurb: "Average True Range estimates how large daily moves have been lately.",
  },
  stochastic: {
    title: "Stochastic",
    blurb: "Position of the close within the recent high-low range, useful for overbought and oversold reads.",
  },
  obv: {
    title: "OBV",
    blurb: "On-Balance Volume tracks whether volume is confirming price direction.",
  },
  fibonacci: {
    title: "Fibonacci Levels",
    blurb: "Common retracement levels used to estimate nearby support and resistance zones.",
  },
  adx: {
    title: "ADX",
    blurb: "Trend-strength indicator showing whether the market is directional or choppy.",
  },
};

const CHART_COLORS = ["#a56a00", "#2f6f65", "#9f3f24", "#7b5ea7"];

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

function formatNumber(value, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(digits);
}

function formatDateLabel(value) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(parsed);
}

function normalizeHistory(response) {
  if (!response || !Array.isArray(response.history)) {
    return [];
  }

  return response.history.slice(-5).reverse();
}

function summarizeIndicator(indicatorKey, payload) {
  if (!payload) {
    return "Signal unavailable";
  }

  switch (indicatorKey) {
    case "moving_averages":
      return `Price ${formatNumber(payload.price)} | MA50 ${formatNumber(payload.ma50)} | MA200 ${formatNumber(payload.ma200)}`;
    case "macd":
      return `MACD ${formatNumber(payload.value, 4)} | Signal ${formatNumber(payload.signal_line, 4)}`;
    case "bollinger_bands":
      return `Upper ${formatNumber(payload.upper)} | Mid ${formatNumber(payload.middle)} | Lower ${formatNumber(payload.lower)}`;
    case "fibonacci":
      return `23.6% ${formatNumber(payload.level_23_6)} | 38.2% ${formatNumber(payload.level_38_2)} | 61.8% ${formatNumber(payload.level_61_8)}`;
    default:
      return `Value ${formatNumber(payload.value, indicatorKey === "atr" || indicatorKey === "macd" ? 4 : 2)}`;
  }
}

function explainIndicator(indicatorKey, payload) {
  if (!payload) {
    return "Current reading is unavailable.";
  }

  switch (indicatorKey) {
    case "rsi":
      if (payload.value > 70) return `RSI at ${formatNumber(payload.value)} suggests overbought conditions and possible exhaustion.`;
      if (payload.value < 30) return `RSI at ${formatNumber(payload.value)} suggests oversold conditions and rebound potential.`;
      return `RSI at ${formatNumber(payload.value)} suggests balanced momentum without an extreme condition.`;
    case "moving_averages":
      if (payload.signal === "BUY") return "Price is trading above both MA50 and MA200, which supports an established uptrend.";
      if (payload.signal === "SELL") return "Price is below both MA50 and MA200, which suggests trend weakness.";
      return "Price is mixed versus MA50 and MA200, so the trend picture is not fully aligned.";
    case "macd":
      if (payload.signal === "BUY") return "MACD is above its signal line, which points to improving upside momentum.";
      return "MACD is below its signal line, which points to fading momentum or a bearish crossover.";
    case "bollinger_bands":
      if (payload.signal === "BUY") return "Price is pressing near the lower band, which can indicate an oversold area.";
      if (payload.signal === "SELL") return "Price is pressing near the upper band, which can indicate an overextended move.";
      return "Price is trading inside the bands without sitting near an extreme.";
    case "momentum":
      if (payload.value > 0) return `Momentum is positive at ${formatNumber(payload.value)}, so recent price change is still pointing upward.`;
      if (payload.value < 0) return `Momentum is negative at ${formatNumber(payload.value)}, so recent price change is still pointing downward.`;
      return "Momentum is flat, so recent price movement is not showing strong acceleration.";
    case "atr":
      if (payload.signal === "HIGH_RISK") return `ATR at ${formatNumber(payload.value, 4)} signals elevated volatility and higher risk per trade.`;
      return `ATR at ${formatNumber(payload.value, 4)} signals relatively contained recent volatility.`;
    case "stochastic":
      if (payload.value > 80) return `Stochastic at ${formatNumber(payload.value)} suggests the market is near the top of its recent range.`;
      if (payload.value < 20) return `Stochastic at ${formatNumber(payload.value)} suggests the market is near the bottom of its recent range.`;
      return `Stochastic at ${formatNumber(payload.value)} shows the close is sitting in the middle of the recent range.`;
    case "obv":
      if (payload.signal === "BUY") return "OBV is rising, which suggests volume is confirming buying pressure.";
      if (payload.signal === "SELL") return "OBV is falling, which suggests volume is not confirming strength.";
      return "OBV is flat, so volume confirmation is limited right now.";
    case "fibonacci":
      if (payload.signal === "BUY") return "Price is sitting near a deeper retracement support zone, which can attract buyers.";
      if (payload.signal === "SELL") return "Price is close to a nearby retracement resistance zone, which can slow upside continuation.";
      return "Price is not especially close to a key Fibonacci support or resistance level.";
    case "adx":
      if (payload.signal === "STRONG_TREND") return `ADX at ${formatNumber(payload.value)} suggests a strong directional trend is in place.`;
      if (payload.signal === "WEAK_TREND") return `ADX at ${formatNumber(payload.value)} suggests a weak or range-bound market.`;
      return `ADX at ${formatNumber(payload.value)} suggests trend strength is present but not especially strong.`;
    default:
      return "This indicator helps add context to the broader technical setup.";
  }
}

function buildPath(points, width, height, padding, globalMin, globalRange) {
  if (points.length < 2) {
    return "";
  }

  const usableWidth = width - padding * 2;

  return points
    .map((point, index) => {
      const x = padding + (index / (points.length - 1)) * usableWidth;
      const y = getYPosition(point.value, globalMin, globalRange, height, padding);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function getChartBounds(series) {
  const values = series.flatMap((line) => (line.points ?? []).map((point) => point.value));
  if (values.length === 0) {
    return { minValue: 0, maxValue: 1, range: 1 };
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || Math.max(Math.abs(maxValue) * 0.1, 1);
  return { minValue, maxValue, range };
}

function getXPosition(index, totalPoints, width, padding) {
  if (totalPoints <= 1) {
    return width / 2;
  }

  const usableWidth = width - padding * 2;
  return padding + (index / (totalPoints - 1)) * usableWidth;
}

function getYPosition(value, minValue, range, height, padding) {
  const usableHeight = height - padding * 2;
  return height - padding - ((value - minValue) / range) * usableHeight;
}

function getNearestTooltipData(series, hoverX, width, padding) {
  const primarySeries = series.find((line) => (line.points ?? []).length > 0);
  const totalPoints = primarySeries?.points?.length ?? 0;
  if (!primarySeries || totalPoints === 0) {
    return null;
  }

  let nearestIndex = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (let index = 0; index < totalPoints; index += 1) {
    const x = getXPosition(index, totalPoints, width, padding);
    const distance = Math.abs(x - hoverX);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestIndex = index;
    }
  }

  const date = primarySeries.points?.[nearestIndex]?.date ?? "";
  const entries = series
    .map((line, idx) => ({
      label: line.label,
      point: line.points?.[nearestIndex] ?? null,
      colorIndex: idx,
    }))
    .filter((entry) => entry.point !== null);

  if (entries.length === 0) {
    return null;
  }

  return { date, index: nearestIndex, entries };
}

function getReferenceLines(indicatorKey, minValue, maxValue) {
  const inRange = (value) => value >= minValue && value <= maxValue;

  switch (indicatorKey) {
    case "rsi":
      return [
        { value: 70, label: "70", style: "overbought" },
        { value: 30, label: "30", style: "oversold" },
      ].filter((line) => inRange(line.value));
    case "stochastic":
      return [
        { value: 80, label: "80", style: "overbought" },
        { value: 20, label: "20", style: "oversold" },
      ].filter((line) => inRange(line.value));
    case "adx":
      return [
        { value: 25, label: "Trend 25", style: "trend" },
        { value: 20, label: "Weak 20", style: "trend" },
      ].filter((line) => inRange(line.value));
    case "macd":
    case "momentum":
    case "obv":
      return inRange(0) ? [{ value: 0, label: "0", style: "baseline" }] : [];
    default:
      return [];
  }
}

function IndicatorChart({ chart, indicatorKey }) {
  const width = 320;
  const height = 180;
  const padding = 20;
  const series = chart?.series ?? [];
  const [hoverX, setHoverX] = useState(null);
  const primarySeries = series.find((line) => (line.points ?? []).length > 0);
  const totalPoints = primarySeries?.points?.length ?? 0;
  const { minValue, maxValue, range } = useMemo(() => getChartBounds(series), [series]);
  const tooltip = hoverX === null ? null : getNearestTooltipData(series, hoverX, width, padding);
  const startDate = primarySeries?.points?.[0]?.date ?? "";
  const endDate = primarySeries?.points?.[totalPoints - 1]?.date ?? "";
  const midDate = primarySeries?.points?.[Math.floor(totalPoints / 2)]?.date ?? "";
  const zeroY =
    minValue <= 0 && maxValue >= 0
      ? getYPosition(0, minValue, range, height, padding)
      : null;
  const hasData = series.some((line) => (line.points ?? []).length > 1);
  const referenceLines = getReferenceLines(indicatorKey, minValue, maxValue);

  if (!hasData) {
    return <div className="chart-empty">Chart unavailable</div>;
  }

  return (
    <div className="chart-shell">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="indicator-svg"
        role="img"
        aria-label="Technical indicator chart"
        onMouseLeave={() => setHoverX(null)}
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const relativeX = ((event.clientX - rect.left) / rect.width) * width;
          setHoverX(relativeX);
        }}
      >
        <rect x="0" y="0" width={width} height={height} rx="18" className="chart-bg" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="chart-axis" />
        {zeroY !== null && <line x1={padding} y1={zeroY} x2={width - padding} y2={zeroY} className="chart-baseline" />}
        {referenceLines.map((line) => {
          const y = getYPosition(line.value, minValue, range, height, padding);
          return (
            <g key={`${indicatorKey}-${line.value}`}>
              <line
                x1={padding}
                y1={y}
                x2={width - padding}
                y2={y}
                className={`chart-reference chart-reference-${line.style}`}
              />
              <text x={width - padding - 2} y={y - 4} textAnchor="end" className="chart-reference-label">
                {line.label}
              </text>
            </g>
          );
        })}
        {series.map((line, index) => {
          const path = buildPath(line.points ?? [], width, height, padding, minValue, range);
          if (!path) {
            return null;
          }

          const isClose = line.label === "Close";
          const strokeColor = isClose ? "#333333" : CHART_COLORS[index % CHART_COLORS.length];
          const strokeWidth = isClose ? "2" : "3";
          const strokeOpacity = isClose ? 0.8 : 1;
          const strokeDash = isClose ? "4 4" : "none";

          return (
            <path
              key={line.label}
              d={path}
              fill="none"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray={strokeDash}
              opacity={strokeOpacity}
            />
          );
        })}
        {tooltip && (
          <>
            <line
              x1={getXPosition(tooltip.index, totalPoints, width, padding)}
              y1={padding}
              x2={getXPosition(tooltip.index, totalPoints, width, padding)}
              y2={height - padding}
              className="chart-cursor"
            />
            {tooltip.entries.map((entry) => (
              <circle
                key={`${entry.label}-${entry.point.date}`}
                cx={getXPosition(tooltip.index, totalPoints, width, padding)}
                cy={getYPosition(entry.point.value, minValue, range, height, padding)}
                r="3.5"
                fill={entry.label === "Close" ? "#333333" : CHART_COLORS[entry.colorIndex % CHART_COLORS.length]}
                className="chart-point"
              />
            ))}
          </>
        )}
        <text x={padding} y={padding - 4} className="chart-label">
          {formatNumber(maxValue, Math.abs(maxValue) < 10 ? 4 : 2)}
        </text>
        <text x={padding} y={height - padding - 4} className="chart-label">
          {formatNumber(minValue, Math.abs(minValue) < 10 ? 4 : 2)}
        </text>
      </svg>

      <div className="chart-dates" aria-hidden="true">
        <span>{formatDateLabel(startDate)}</span>
        <span>{formatDateLabel(midDate)}</span>
        <span>{formatDateLabel(endDate)}</span>
      </div>

      {tooltip && (
        <div className="chart-tooltip">
          <strong>{formatDateLabel(tooltip.date)}</strong>
          {tooltip.entries.map((entry) => (
            <span className="tooltip-row" key={`${entry.label}-${entry.point.date}`}>
              <span
                className="legend-dot"
                style={{ backgroundColor: entry.label === "Close" ? "#333333" : CHART_COLORS[entry.colorIndex % CHART_COLORS.length] }}
              />
              {entry.label}: {formatNumber(entry.point.value, Math.abs(entry.point.value) < 10 ? 4 : 2)}
            </span>
          ))}
        </div>
      )}

      <div className="chart-legend">
        {series.map((line, index) => (
          <span className="legend-item" key={line.label}>
            <span className="legend-dot" style={{ backgroundColor: line.label === "Close" ? "#333333" : CHART_COLORS[index % CHART_COLORS.length] }} />
            {line.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function IndicatorInfo({ title, blurb, explanation }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="indicator-info">
      <button
        type="button"
        className="info-button"
        aria-expanded={open}
        aria-label={`What ${title} means`}
        onClick={() => setOpen((current) => !current)}
      >
        i
      </button>
      {open && (
        <div className="info-popover">
          <strong>{title}</strong>
          <p>{blurb}</p>
          <p>{explanation}</p>
        </div>
      )}
    </div>
  );
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

        const price = priceResult.status === "fulfilled" ? priceResult.value : null;
        const prediction = predictionResult.status === "fulfilled" ? predictionResult.value : null;
        const sentiment = sentimentResult.status === "fulfilled" ? sentimentResult.value : null;
        const historyResponse = historyResult.status === "fulfilled" ? historyResult.value : null;

        const wasAborted =
          abortController.signal.aborted ||
          [priceResult, predictionResult, sentimentResult, historyResult].some(
            (result) => result.status === "rejected" && result.reason?.name === "AbortError",
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

  const indicatorSummary = dashboard.prediction?.indicator_summary ?? { bullish: 0, bearish: 0, neutral: 0 };
  const technicalIndicators = dashboard.prediction?.technical_indicators ?? {};
  const indicatorCharts = dashboard.prediction?.indicator_charts ?? {};

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-brand">
          <img className="hero-logo" src="/goldhelm-logo.png" alt="GoldHelm AI logo" />
          <div className="hero-copy">
            <p className="eyebrow">GoldHelm AI</p>
            <h1>Gold intelligence with explainable next-day forecasts.</h1>
            <p className="hero-text">
              Track the latest futures close, view recent history, inspect the model&apos;s next-session prediction,
              and review the full technical indicator stack in one place.
            </p>
          </div>
        </div>
      </section>

      {loading && <p className="status">Loading market data...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && hasDashboardData && (
        <>
          <section className="cards cards-wide">
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
              <p className="card-meta">Expected move: {dashboard.prediction?.predicted_change_pct?.toFixed(3)}%</p>
            </article>

            <article className="card">
              <p className="card-label">Model Quality</p>
              <h2>{formatPercent((dashboard.prediction?.confidence ?? NaN) * 100)}</h2>
              <p className="card-meta">Validation MAE: {formatCurrency(dashboard.prediction?.validation_mae)}</p>
              <p className="card-meta">Risk: {(dashboard.prediction?.risk_level || "low").toUpperCase()}</p>
            </article>

            <article className="card">
              <p className="card-label">Market Sentiment</p>
              <h2 className="sentiment-label">{dashboard.sentiment?.label || dashboard.prediction?.sentiment?.label || "Neutral"}</h2>
              <p className="card-meta">
                Score:{" "}
                {typeof (dashboard.sentiment?.score ?? dashboard.prediction?.sentiment?.score) === "number"
                  ? (dashboard.sentiment?.score ?? dashboard.prediction?.sentiment?.score).toFixed(3)
                  : "N/A"}
              </p>
            </article>

            <article className="card decision-card">
              <p className="card-label">Final Decision</p>
              <h2 className="decision-label">{dashboard.prediction?.decision || "HOLD"}</h2>
              <p className="card-meta">Combined confidence: {formatPercent((dashboard.prediction?.confidence ?? NaN) * 100)}</p>
              <p className="card-meta">RL suggestion: {dashboard.prediction?.rl_decision || "Unavailable"}</p>
            </article>
          </section>

          <section className="insight-panel">
            <div className="section-heading">
              <h3>Final Analysis</h3>
              <p>Coordinator output combining reasoning, reinforcement learning, and technical structure.</p>
            </div>

            <div className="explanation-list">
              {(dashboard.prediction?.final_analysis ?? []).length > 0 ? (
                dashboard.prediction.final_analysis.map((reason) => (
                  <article className="explanation-row" key={reason}>
                    {reason}
                  </article>
                ))
              ) : (
                <article className="explanation-row">Final analysis will appear when the prediction endpoint provides it.</article>
              )}
            </div>
          </section>

          <section className="indicator-panel">
            <div className="section-heading">
              <h3>Technical Indicator Stack</h3>
              <p>Ten charted indicators computed from the latest OHLCV history in the backend.</p>
            </div>

            <div className="summary-strip">
              <article className="summary-chip bullish-chip">
                <span className="chip-label">Bullish</span>
                <strong>{indicatorSummary.bullish}</strong>
              </article>
              <article className="summary-chip bearish-chip">
                <span className="chip-label">Bearish</span>
                <strong>{indicatorSummary.bearish}</strong>
              </article>
              <article className="summary-chip neutral-chip">
                <span className="chip-label">Neutral</span>
                <strong>{indicatorSummary.neutral}</strong>
              </article>
            </div>

            <div className="indicator-grid">
              {INDICATOR_ORDER.map((key) => {
                const indicator = technicalIndicators[key];
                const chart = indicatorCharts[key];
                const title = INDICATOR_META[key]?.title || key;
                const blurb = INDICATOR_META[key]?.blurb || "Technical context for this indicator.";
                const signal = indicator?.signal || "HOLD";
                const explanation = explainIndicator(key, indicator);

                return (
                  <article className="indicator-card" key={key}>
                    <div className="indicator-header">
                      <div className="indicator-heading">
                        <div>
                        <p className="card-label">{title}</p>
                        <p className="indicator-meta">{summarizeIndicator(key, indicator)}</p>
                        </div>
                        <IndicatorInfo title={title} blurb={blurb} explanation={explanation} />
                      </div>
                      <span className={`signal-pill signal-${signal.toLowerCase().replace(/_/g, "-")}`}>
                        {signal}
                      </span>
                    </div>
                    <IndicatorChart chart={chart} indicatorKey={key} />
                  </article>
                );
              })}
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
                <p className="card-meta">Confidence: {formatPercent((dashboard.prediction?.debate?.reasoning_agent?.confidence ?? NaN) * 100)}</p>
              </article>

              <article className="debate-card">
                <p className="card-label">RL Agent</p>
                <h4>{dashboard.prediction?.debate?.rl_agent?.decision || "N/A"}</h4>
                <p className="card-meta">Confidence: {formatPercent((dashboard.prediction?.debate?.rl_agent?.confidence ?? NaN) * 100)}</p>
                <p className="card-meta">Policy: {dashboard.prediction?.debate?.policy_source || "Unavailable"}</p>
              </article>

              <article className="debate-card">
                <p className="card-label">Agreement</p>
                <h4>{dashboard.prediction?.debate?.agreement ? "Aligned" : "Mixed"}</h4>
                <p className="card-meta">Coordinator resolves disagreements by defaulting to caution.</p>
              </article>
            </div>
          </section>

          <section className="backtest-panel">
            <div className="section-heading">
              <h3>RL Backtest</h3>
              <p>Offline policy evaluation from the trained trading environment.</p>
            </div>

            <div className="backtest-grid backtest-grid-extended">
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
                <p className="card-label">Sharpe Ratio</p>
                <h4>{formatNumber(dashboard.prediction?.backtest?.sharpe_ratio)}</h4>
              </article>
              <article className="backtest-card">
                <p className="card-label">Max Drawdown</p>
                <h4>{formatPercent((dashboard.prediction?.backtest?.max_drawdown ?? NaN) * 100)}</h4>
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
