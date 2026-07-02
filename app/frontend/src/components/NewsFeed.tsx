import type { NewsItem } from '../types'
import type { useT } from '../i18n'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

interface Props { news: NewsItem[]; ticker: string; t: ReturnType<typeof useT> }

const CAT_BADGE: Record<string, string> = {
  general: 'badge-blue',
  merger:  'badge-purple',
  ipo:     'badge-amber',
  forex:   'badge-green',
  macro:   'badge-rose',
}

function timeAgo(iso: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return '—'
    return formatDistanceToNow(d, { addSuffix: true })
  } catch { return '—' }
}

function SourceDot({ source }: { source: string | null }) {
  const s = (source ?? '').toLowerCase()
  const color = s.includes('reuters') ? '#f59e0b'
    : s.includes('bloomberg') ? '#3b82f6'
    : s.includes('google') ? '#22c55e'
    : '#6b85a8'
  return <span style={{ color }} className="mr-1.5">●</span>
}

export default function NewsFeed({ news, ticker, t }: Props) {
  const relevant = news.filter(n => n.related_tickers?.includes(ticker))
  const rest = news.filter(n => !n.related_tickers?.includes(ticker))
  const sorted = [...relevant, ...rest].slice(0, 15)

  return (
    <div className="glass rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 h-10 border-b border-white/[0.06] flex items-center gap-3"
        style={{ background: 'rgba(255,255,255,0.015)' }}>
        <span className="label">{t.news}</span>
        <span className="label text-[#2d4560]">·</span>
        <span className="font-mono text-[10px] text-[#4a6282]">{sorted.length} items</span>
        {relevant.length > 0 && (
          <span className="badge badge-blue ml-1">{relevant.length} related to {ticker}</span>
        )}
      </div>

      {/* Grid */}
      <div className="p-3 grid grid-cols-3 gap-2.5 max-h-72 overflow-y-auto">
        {sorted.map((item, i) => {
          const isRel = item.related_tickers?.includes(ticker)
          const cat = item.category ?? 'general'
          return (
            <a key={i} href={item.url ?? '#'} target="_blank" rel="noreferrer"
              className={clsx('news-card', isRel && '!border-blue-500/15 !bg-blue-500/[0.025]')}>
              {/* Meta row */}
              <div className="flex items-center gap-1.5 mb-2">
                <span className={clsx('badge', CAT_BADGE[cat] ?? 'badge-blue')}>{cat}</span>
                {isRel && <span className="badge badge-green">match</span>}
                <span className="font-mono text-[9px] text-[#64748b] ml-auto">{timeAgo(item.published_at)}</span>
              </div>
              {/* Headline */}
              <p className="text-[11px] text-[#94a3b8] leading-relaxed line-clamp-3 mb-2">{item.headline}</p>
              {/* Source */}
              <div className="text-[10px] text-[#64748b]">
                <SourceDot source={item.source} />
                {item.source ?? item.api_source}
              </div>
            </a>
          )
        })}
      </div>
    </div>
  )
}
