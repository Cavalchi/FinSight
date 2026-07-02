import type { Lang } from '../types'
import type { useT } from '../i18n'
import type { TickerMeta } from '../api'
import clsx from 'clsx'

const LANG_OPTIONS: { value: Lang; flag: string }[] = [
  { value: 'EN', flag: '🇬🇧' },
  { value: 'PT', flag: '🇧🇷' },
  { value: 'ES', flag: '🇪🇸' },
]

const PIPELINE = [
  { label: 'Prices',   ok: true },
  { label: 'News',     ok: true },
  { label: 'dbt',      ok: true },
  { label: 'RAG / AI', ok: true },
]

interface Props {
  tickers: string[]
  selected: string
  onSelect: (t: string) => void
  lang: Lang
  onLangChange: (l: Lang) => void
  t: ReturnType<typeof useT>
  tickerMeta: Record<string, TickerMeta>
}

export default function Sidebar({ tickers, selected, onSelect, lang, onLangChange, t, tickerMeta }: Props) {
  return (
    <aside className="w-64 flex-shrink-0 flex flex-col border-r border-white/[0.06] relative z-20"
      style={{ background: 'rgba(6,11,22,0.92)', backdropFilter: 'blur(20px)' }}>

      {/* Logo */}
      <div className="px-4 h-14 flex items-center gap-3 border-b border-white/[0.06] flex-shrink-0">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-black text-white flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}>
          F
        </div>
        <div>
          <div className="font-bold text-base grad-text leading-none">FinSight</div>
          <div className="label mt-0.5">Data Pipeline</div>
        </div>
      </div>

      {/* Assets header */}
      <div className="px-4 pt-4 pb-1.5">
        <span className="label">Assets ({tickers.length})</span>
      </div>

      {/* Ticker list */}
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {tickers.map(ticker => {
          const name = tickerMeta[ticker]?.name || ticker
          const isActive = ticker === selected
          return (
            <button key={ticker} onClick={() => onSelect(ticker)}
              className={clsx('ticker-pill', isActive && 'active')}>
              <div className="flex-1 min-w-0">
                <div className={clsx('text-sm font-semibold truncate leading-snug',
                  isActive ? 'text-white' : 'text-[#8ba3c0]')}>
                  {name}
                </div>
              </div>
              {isActive && <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />}
            </button>
          )
        })}
      </div>

      {/* Pipeline status */}
      <div className="px-4 py-3 border-t border-white/[0.06]">
        <div className="label mb-2">Pipeline</div>
        <div className="space-y-2">
          {PIPELINE.map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full flex-shrink-0',
                item.ok ? 'bg-emerald-500 pulse-dot' : 'bg-[#4a6080]'
              )} />
              <span className={clsx('text-xs', item.ok ? 'text-[#7a96b8]' : 'text-[#4a6080]')}>
                {item.label}
              </span>
              <span className={clsx(
                'ml-auto font-mono text-[9px] font-semibold tracking-wider uppercase',
                item.ok ? 'text-emerald-500' : 'text-[#4a6080]'
              )}>
                {item.ok ? '● live' : '○ soon'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Language + footer */}
      <div className="px-4 pb-4 border-t border-white/[0.06] pt-3">
        <div className="label mb-2">{t.langLabel}</div>
        <div className="flex gap-1.5">
          {LANG_OPTIONS.map(opt => (
            <button key={opt.value} onClick={() => onLangChange(opt.value)}
              className={clsx(
                'flex-1 text-xs py-1.5 rounded-md border transition-all font-semibold',
                lang === opt.value
                  ? 'bg-blue-500/15 border-blue-500/35 text-blue-300'
                  : 'border-white/[0.06] text-[#4a6080] hover:text-[#8ba3c0] hover:border-white/10 bg-transparent'
              )}>
              {opt.flag}
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
