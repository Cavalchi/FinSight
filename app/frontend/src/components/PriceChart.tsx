import { useEffect, useRef } from 'react'
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts'
import type { DayMetric } from '../types'
import type { useT } from '../i18n'

interface Props { data: DayMetric[]; t: ReturnType<typeof useT> }

export default function PriceChart({ data, t }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data.length) return

    // Cleanup previous
    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 380,
      layout: {
        background: { color: 'transparent' },
        textColor: '#4a6282',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.03)' },
        horzLines: { color: 'rgba(255,255,255,0.03)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(99,179,237,0.4)', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#0c1628' },
        horzLine: { color: 'rgba(99,179,237,0.4)', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#0c1628' },
      },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)' },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    })
    chartRef.current = chart

    // Candlestick
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    })

    // SMA 7
    const sma7Series = chart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: t.sma7Label,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // SMA 30
    const sma30Series = chart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 2,
      title: t.sma30Label,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Set data
    candleSeries.setData(
      data.map(d => ({
        time: d.trade_date as any,
        open: d.open_price, high: d.high_price,
        low: d.low_price,  close: d.close_price,
      }))
    )

    sma7Series.setData(
      data.filter(d => d.sma_7d != null)
        .map(d => ({ time: d.trade_date as any, value: d.sma_7d! }))
    )

    sma30Series.setData(
      data.filter(d => d.sma_30d != null)
        .map(d => ({ time: d.trade_date as any, value: d.sma_30d! }))
    )

    chart.timeScale().fitContent()

    // Resize
    const observer = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, 380)
      }
    })
    observer.observe(containerRef.current)

    return () => { observer.disconnect(); chart.remove(); chartRef.current = null }
  }, [data, t])

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Chart header */}
      <div className="px-5 py-3 border-b border-white/[0.05] flex items-center gap-4">
        <span className="text-xs font-semibold text-[#7b9bc0] uppercase tracking-wider">{t.priceChart}</span>
        <div className="flex items-center gap-4 ml-auto">
          <Legend color="#10b981" label={t.ohlc} />
          <Legend color="#f59e0b" label={t.sma7Label} dashed />
          <Legend color="#3b82f6" label={t.sma30Label} />
        </div>
      </div>
      <div ref={containerRef} className="w-full" />
    </div>
  )
}

function Legend({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="w-6 h-0.5 rounded-full"
        style={{
          background: color,
          borderTop: dashed ? `2px dashed ${color}` : undefined,
          height: dashed ? 0 : 2,
        }}
      />
      <span className="text-[11px] text-[#4a6282] font-mono">{label}</span>
    </div>
  )
}
