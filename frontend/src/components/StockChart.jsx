import { useEffect, useRef } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
  LineStyle,
} from "lightweight-charts";

// Styling per overlay key. Levels are horizontal dashed/dotted price lines.
const LINE_STYLES = {
  sma_20: { color: "#2962ff", title: "SMA 20" },
  sma_50: { color: "#f39c12", title: "SMA 50" },
  bb_upper: { color: "#78909c", title: "BB upper" },
  bb_lower: { color: "#78909c", title: "BB lower" },
};

const LEVEL_STYLES = {
  support: { color: "#2e8b57", style: LineStyle.Dashed, title: "support" },
  resistance: { color: "#c0392b", style: LineStyle.Dashed, title: "resistance" },
  fib_236: { color: "#9b59b6", style: LineStyle.Dotted, title: "fib 23.6%" },
  fib_382: { color: "#9b59b6", style: LineStyle.Dotted, title: "fib 38.2%" },
  fib_500: { color: "#9b59b6", style: LineStyle.Dotted, title: "fib 50%" },
  fib_618: { color: "#9b59b6", style: LineStyle.Dotted, title: "fib 61.8%" },
  fib_786: { color: "#9b59b6", style: LineStyle.Dotted, title: "fib 78.6%" },
};

export default function StockChart({ chart }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !chart?.candles?.length) return;

    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    // Intraday bars arrive as Unix timestamps; daily/weekly as date strings.
    const intraday = typeof chart.candles[0].time === "number";
    const lwChart = createChart(containerRef.current, {
      height: 480, // price pane + RSI pane below

      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: dark ? "#ccc" : "#333",
      },
      grid: {
        vertLines: { color: dark ? "#ffffff14" : "#00000010" },
        horzLines: { color: dark ? "#ffffff14" : "#00000010" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: intraday, secondsVisible: false },
    });

    const candleSeries = lwChart.addSeries(CandlestickSeries, {
      upColor: "#2e8b57",
      downColor: "#c0392b",
      borderVisible: false,
      wickUpColor: "#2e8b57",
      wickDownColor: "#c0392b",
    });
    candleSeries.setData(chart.candles);

    // Volume as a histogram pinned to the bottom 20% of the pane.
    const volumeSeries = lwChart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    lwChart.priceScale("").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volumeSeries.setData(chart.volume);

    // RSI renders in its own pane (0-100 scale); everything else overlays price.
    const { rsi_14: rsiPoints, ...mainLines } = chart.lines ?? {};

    for (const [key, points] of Object.entries(mainLines)) {
      const style = LINE_STYLES[key] ?? { color: "#888" };
      const line = lwChart.addSeries(LineSeries, {
        color: style.color,
        lineWidth: 1.5,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      line.setData(points);
    }

    if (rsiPoints?.length) {
      const rsiSeries = lwChart.addSeries(
        LineSeries,
        {
          color: "#9b59b6",
          lineWidth: 1.5,
          priceLineVisible: false,
          crosshairMarkerVisible: false,
        },
        1 // pane index 1: separate panel below the price pane
      );
      rsiSeries.setData(rsiPoints);
      // Overbought/oversold guide bands.
      rsiSeries.createPriceLine({
        price: 70, color: "#c0392b88", lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "70",
      });
      rsiSeries.createPriceLine({
        price: 30, color: "#2e8b5788", lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "30",
      });
      const rsiPane = lwChart.panes()[1];
      if (rsiPane?.setHeight) rsiPane.setHeight(110);
    }

    for (const [key, price] of Object.entries(chart.levels ?? {})) {
      const style = LEVEL_STYLES[key] ?? { color: "#888", style: LineStyle.Dashed, title: key };
      candleSeries.createPriceLine({
        price,
        color: style.color,
        lineWidth: 1,
        lineStyle: style.style,
        axisLabelVisible: true,
        title: style.title,
      });
    }

    // Signal markers: ▲ under bullish bars, ▼ above bearish bars.
    if (chart.signals?.length) {
      createSeriesMarkers(
        candleSeries,
        chart.signals.map((s) => ({
          time: s.time,
          position: s.direction === "bullish" ? "belowBar" : "aboveBar",
          shape: s.direction === "bullish" ? "arrowUp" : "arrowDown",
          color: s.direction === "bullish" ? "#2e8b57" : "#c0392b",
        }))
      );
    }

    lwChart.timeScale().fitContent();

    // Keep width in sync with the container.
    const ro = new ResizeObserver((entries) => {
      lwChart.applyOptions({ width: entries[0].contentRect.width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      lwChart.remove();
    };
  }, [chart]);

  if (!chart?.candles?.length) return null;
  return <div className="stock-chart" ref={containerRef} />;
}
