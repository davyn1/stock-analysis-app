// All calls go through the Vite dev proxy (/api -> http://localhost:8000),
// so there's nothing to configure and no CORS to worry about in dev.
const BASE = "/api";

// Abort requests that hang (e.g. a dropped connection mid-request) so the UI
// shows an error instead of spinning forever.
function withTimeout(ms = 30000) {
  return AbortSignal.timeout(ms);
}

async function parseOrThrow(res, fallbackMsg) {
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(json.detail || `${fallbackMsg} (${res.status})`);
  }
  return json;
}

// /trading/* is guarded by an auth seam that's open in local dev and enforced
// once a token is configured. Send the token when one is provided at build time
// (VITE_TRADING_TOKEN); harmless when the endpoint is open.
function tradingHeaders(extra = {}) {
  const token = import.meta.env.VITE_TRADING_TOKEN;
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

export async function fetchChart(symbol, interval, level) {
  const params = new URLSearchParams({ interval, level });
  let res;
  try {
    res = await fetch(`${BASE}/chart/${encodeURIComponent(symbol)}?${params}`, {
      signal: withTimeout(),
    });
  } catch (err) {
    throw new Error(err.name === "TimeoutError" ? "Chart request timed out — try again." : err.message);
  }
  return parseOrThrow(res, "Chart request failed");
}

export async function analyze({ symbol, level }) {
  let res;
  try {
    res = await fetch(`${BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, level }),
      signal: withTimeout(60000), // first analyze includes a Gemini call; give it longer
    });
  } catch (err) {
    throw new Error(err.name === "TimeoutError" ? "Analysis timed out — try again." : err.message);
  }
  return parseOrThrow(res, "Request failed");
}

export async function fetchStrategies() {
  let res;
  try {
    res = await fetch(`${BASE}/trading/strategies`, {
      headers: tradingHeaders(),
      signal: withTimeout(),
    });
  } catch (err) {
    throw new Error(err.name === "TimeoutError" ? "Request timed out — try again." : err.message);
  }
  return parseOrThrow(res, "Could not load strategies");
}

export async function runBacktest({ symbol, strategy }) {
  let res;
  try {
    res = await fetch(`${BASE}/trading/backtest`, {
      method: "POST",
      headers: tradingHeaders({ "Content-Type": "application/json" }),
      // A backtest may fetch a few years of history on first run for a symbol.
      body: JSON.stringify({ symbol, strategy }),
      signal: withTimeout(60000),
    });
  } catch (err) {
    throw new Error(err.name === "TimeoutError" ? "Backtest timed out — try again." : err.message);
  }
  return parseOrThrow(res, "Backtest failed");
}
