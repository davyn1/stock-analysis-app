import { useEffect, useRef } from "react";
import { createChart, LineSeries, ColorType } from "lightweight-charts";

// Account-value curves over the backtest window: the strategy vs buy-and-hold.
// Same lightweight-charts API as StockChart, kept separate because this is a
// plain value line (no candles/panes) on the backtest's own time axis.
export default function EquityChart({ equity, benchmark }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !equity?.length) return;

    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const chart = createChart(containerRef.current, {
      height: 240,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: dark ? "#ccc" : "#333",
      },
      grid: {
        vertLines: { color: dark ? "#ffffff14" : "#00000010" },
        horzLines: { color: dark ? "#ffffff14" : "#00000010" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });

    // Buy-and-hold first, so the strategy line sits on top.
    const bh = chart.addSeries(LineSeries, {
      color: "#8894",
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    bh.setData(benchmark ?? []);

    const strat = chart.addSeries(LineSeries, {
      color: "#2e8b57",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    strat.setData(equity);

    chart.timeScale().fitContent();

    const ro = new ResizeObserver((entries) => {
      chart.applyOptions({ width: entries[0].contentRect.width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [equity, benchmark]);

  if (!equity?.length) return null;
  return (
    <div className="equity-chart-wrap">
      <div className="equity-legend">
        <span className="legend-item strat">Strategy</span>
        <span className="legend-item bench">Buy &amp; hold</span>
      </div>
      <div className="equity-chart" ref={containerRef} />
    </div>
  );
}
