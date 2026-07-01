import { useState, useEffect } from 'react'
import { fetchTickers, fetchMetrics, fetchNews } from './api'
import { TICKER_INFO } from './types'
import type { DayMetric, NewsItem, Lang, Period } from './types'
import { useT } from './i18n'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import KpiGrid from './components/KpiGrid'
import PriceChart from './components/PriceChart'
import MetricsCharts from './components/MetricsCharts'
import NewsFeed from './components/NewsFeed'
import RagSection from './components/RagSection'

export default function App() {
  const [lang, setLang] = useState<Lang>('EN')
  const [tickers, setTickers] = useState<string[]>([])
  const [selected, setSelected] = useState<string>('')
  const [metrics, setMetrics] = useState<DayMetric[]>([])
  const [news, setNews] = useState<NewsItem[]>([])
  const [period, setPeriod] = useState<Period>('ALL')
  const [loading, setLoading] = useState(true)
  const t = useT(lang)

  // Load tickers + news once
  useEffect(() => {
    Promise.all([fetchTickers(), fetchNews()]).then(([ticks, n]) => {
      setTickers(ticks)
      setNews(n)
      if (ticks.length > 0) setSelected(ticks[0])
    })
  }, [])

  // Load metrics when selected changes
  useEffect(() => {
    if (!selected) return
    setLoading(true)
    fetchMetrics(selected)
      .then(setMetrics)
      .finally(() => setLoading(false))
  }, [selected])

  // Filter by period
  const filtered = (() => {
    if (!metrics.length) return metrics
    const last = new Date(metrics[metrics.length - 1].trade_date)
    if (period === '7D') {
      const cutoff = new Date(last); cutoff.setDate(cutoff.getDate() - 7)
      return metrics.filter(d => new Date(d.trade_date) >= cutoff)
    }
    if (period === '1M') {
      const cutoff = new Date(last); cutoff.setMonth(cutoff.getMonth() - 1)
      return metrics.filter(d => new Date(d.trade_date) >= cutoff)
    }
    if (period === '3M') {
      const cutoff = new Date(last); cutoff.setMonth(cutoff.getMonth() - 3)
      return metrics.filter(d => new Date(d.trade_date) >= cutoff)
    }
    return metrics
  })()

  const latest = filtered[filtered.length - 1]
  const info = TICKER_INFO[selected] ?? { name: selected, flag: '📊', sector: '—' }

  return (
    <div className="flex h-screen overflow-hidden bg-base text-white relative">
      {/* Aurora animated background */}
      <div className="aurora" />

      {/* Sidebar */}
      <Sidebar
        tickers={tickers}
        selected={selected}
        onSelect={setSelected}
        lang={lang}
        onLangChange={setLang}
        t={t}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* Accent bar */}
        <div className="accent-bar w-full flex-shrink-0" />

        <TopBar info={info} ticker={selected} latest={latest} period={period} setPeriod={setPeriod} t={t} />

        <div className="flex-1 overflow-y-auto px-6 pb-8 space-y-6 pt-5">
          {loading ? (
            <LoadingSkeleton />
          ) : !latest ? (
            <EmptyState t={t} />
          ) : (
            <>
              <KpiGrid latest={latest} t={t} />
              <PriceChart data={filtered} t={t} />
              <MetricsCharts data={filtered} t={t} />
              <NewsFeed news={news} ticker={selected} t={t} />
              <RagSection t={t} />
            </>
          )}
        </div>
      </main>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-5 pt-2">
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton h-24 rounded-xl" />
        ))}
      </div>
      <div className="skeleton h-96 rounded-xl" />
      <div className="grid grid-cols-2 gap-4">
        <div className="skeleton h-52 rounded-xl" />
        <div className="skeleton h-52 rounded-xl" />
      </div>
    </div>
  )
}

function EmptyState({ t }: { t: ReturnType<typeof useT> }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="text-4xl mb-4">📭</div>
      <p className="text-[#7b9bc0] text-sm">{t.noData}</p>
    </div>
  )
}
