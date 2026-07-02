import { useState, useEffect } from 'react'
import { fetchTickers, fetchMetrics, fetchNews, fetchTickerMeta } from './api'
import type { TickerMeta } from './api'
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
import clsx from 'clsx'

export default function App() {
  const [lang, setLang] = useState<Lang>('EN')
  const [tickers, setTickers] = useState<string[]>([])
  const [selected, setSelected] = useState<string>('')
  const [metrics, setMetrics] = useState<DayMetric[]>([])
  const [news, setNews] = useState<NewsItem[]>([])
  const [period, setPeriod] = useState<Period>('ALL')
  const [loading, setLoading] = useState(true)
  const [aiMode, setAiMode]   = useState(false)
  const [tickerMeta, setTickerMeta] = useState<Record<string, TickerMeta>>({})
  const t = useT(lang)

  // Load tickers + news once
  useEffect(() => {
    Promise.all([fetchTickers(), fetchNews(), fetchTickerMeta()]).then(([ticks, n, meta]) => {
      setTickers(ticks)
      setNews(n)
      // Build lookup map ticker -> meta
      const metaMap: Record<string, TickerMeta> = {}
      meta.forEach(m => { metaMap[m.ticker] = m })
      setTickerMeta(metaMap)
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
      {/* Aurora */}
      <div className="aurora" />

      {/* Sidebar */}
      <Sidebar
        tickers={tickers}
        selected={selected}
        onSelect={setSelected}
        lang={lang}
        onLangChange={setLang}
        t={t}
        tickerMeta={tickerMeta}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
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

              {/* ── CTA para IA ── */}
              <div className="flex flex-col items-center gap-3 py-8">
                <div className="w-px h-8 bg-gradient-to-b from-transparent to-white/10" />
                <button
                  onClick={() => setAiMode(true)}
                  className="group flex items-center gap-3 px-6 py-3 rounded-2xl border border-white/10 hover:border-blue-500/40 transition-all duration-300 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
                  style={{ background: 'rgba(8,15,30,0.8)' }}
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 transition-all duration-300 group-hover:shadow-[0_0_20px_rgba(139,92,246,0.4)]"
                    style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)' }}
                  >
                    ✦
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-white">Perguntar ao Analista IA</div>
                    <div className="text-[11px] text-[#4a6282]">Respostas fundamentadas nos dados do seu pipeline</div>
                  </div>
                  <span className="text-[#2d4560] group-hover:text-blue-400 transition-colors ml-2">→</span>
                </button>
                <div className="w-px h-8 bg-gradient-to-t from-transparent to-white/10" />
              </div>
            </>
          )}
        </div>
      </main>

      {/* ── AI OVERLAY — tela cheia ao clicar no CTA ── */}
      {aiMode && (
        <div
          className="fixed inset-0 z-50 flex flex-col"
          style={{ background: 'rgba(3,6,16,0.98)', backdropFilter: 'blur(24px)' }}
        >
          {/* Linha decorativa no topo */}
          <div className="h-px w-full flex-shrink-0"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(139,92,246,0.5), rgba(59,130,246,0.5), transparent)' }}
          />

          {/* Topbar da IA */}
          <div className="flex items-center justify-between px-8 h-12 flex-shrink-0 border-b border-white/[0.04]">
            <div className="flex items-center gap-2.5">
              <div className="w-5 h-5 rounded-md flex items-center justify-center text-xs"
                style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)' }}>✦</div>
              <span className="text-sm font-semibold text-white">FinSight AI Analyst</span>
              <span className="text-[10px] font-mono ml-1" style={{ color: 'var(--text-muted)' }}>· {selected} ({info.name})</span>
            </div>
            <button
              onClick={() => setAiMode(false)}
              className="flex items-center gap-1.5 text-xs text-[#4a6282] hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-white/5 hover:border-white/15"
            >
              ← Voltar ao dashboard
            </button>
          </div>

          {/* Conteúdo IA */}
          <div className="flex-1 overflow-y-auto px-8 py-6 max-w-4xl mx-auto w-full">
            <RagSection ticker={selected} t={t} />
          </div>
        </div>
      )}
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
