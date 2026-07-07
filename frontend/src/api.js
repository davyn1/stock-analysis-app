// All calls go through the Vite dev proxy (/api -> http://localhost:8000),
// so there's nothing to configure and no CORS to worry about in dev.
const BASE = "/api";

export async function analyze({ symbol, level }) {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, level }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(json.detail || `Request failed (${res.status})`);
  }
  return json;
}
