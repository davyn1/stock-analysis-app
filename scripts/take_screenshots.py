"""Capture README screenshots from the running app with headless Chromium.

Dev-only — Playwright is NOT in backend/requirements.txt. One-time setup:
    pip install playwright
    playwright install chromium

With the backend (:8000) and frontend (:5173) running:
    python scripts/take_screenshots.py [--url http://localhost:5173] [--symbol AAPL]

Writes PNGs to docs/screenshots/, once per theme (dark ones end in -dark). Fails loudly if the app shows an error or the
explanation is the raw fallback (missing key / LLM error), so a bad capture
never silently ends up in the README.
"""
import argparse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
VIEWPORT = {"width": 1440, "height": 900}
# Canvases need a beat after mount for lightweight-charts to finish drawing.
CHART_SETTLE_MS = 1500


def analyze(page: Page, symbol: str, level: str) -> None:
    """Submit the form and wait until the explanation and chart are fully loaded."""
    page.fill(".analyze-form input", symbol)
    page.select_option(".analyze-form select", level)
    page.click(".analyze-form button[type=submit]")

    # Analyze can include an LLM call; give it the same 60s the frontend allows.
    page.wait_for_selector(".explanation, .error-box", timeout=60_000)
    if page.locator(".error-box").count():
        raise RuntimeError(f"App error: {page.inner_text('.error-box')}")

    explanation = page.inner_text(".explanation").strip()
    # raw_fallback() output starts with "[reason]" — never screenshot that.
    if not explanation or explanation.startswith("["):
        raise RuntimeError(f"Explanation not generated ({level}): {explanation[:120]!r}")

    page.wait_for_selector(".stock-chart canvas")
    page.wait_for_selector(".tf-status", state="detached")
    page.wait_for_timeout(CHART_SETTLE_MS)


def capture(page: Page, selector: str, name: str) -> None:
    path = OUT_DIR / name
    page.locator(selector).first.screenshot(path=path)
    print(f"saved {path.relative_to(OUT_DIR.parent.parent).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--symbol", default="AAPL")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # The app follows prefers-color-scheme, so emulating it captures each
        # theme; the README picks one per viewer with <picture>.
        for scheme, suffix in (("light", ""), ("dark", "-dark")):
            context = browser.new_context(viewport=VIEWPORT, color_scheme=scheme)
            page = context.new_page()
            page.goto(args.url)
            page.click(".landing-cta")

            # Beginner pass: full page view, beginner explanation, candlestick chart.
            analyze(page, args.symbol, "beginner")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=OUT_DIR / f"analysis{suffix}.png")
            print(f"saved docs/screenshots/analysis{suffix}.png")
            capture(page, ".explanation", f"explanation-beginner{suffix}.png")
            capture(page, ".stock-chart", f"chart{suffix}.png")

            # Advanced pass: same ticker, deeper explanation.
            analyze(page, args.symbol, "advanced")
            capture(page, ".explanation", f"explanation-advanced{suffix}.png")

            # Backtester: run the default strategy and wait for the equity curve.
            page.click(".backtester .bt-controls button")
            page.wait_for_selector(".bt-result, .backtester .error", timeout=60_000)
            if page.locator(".backtester .error").count():
                raise RuntimeError(f"Backtest error: {page.inner_text('.backtester .error')}")
            page.wait_for_selector(".equity-chart canvas")
            page.wait_for_timeout(CHART_SETTLE_MS)
            capture(page, ".backtester", f"backtester{suffix}.png")

            context.close()

        browser.close()


if __name__ == "__main__":
    main()
