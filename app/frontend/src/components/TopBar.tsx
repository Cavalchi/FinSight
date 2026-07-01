import clsx from 'clsx'
import type { DayMetric, Period } from '../types'
import type { useT } from '../i18n'

interface Props {
  info: { name: string; flag: string; sector: string }
  ticker: string
  latest: DayMetric | undefined
  period: Period
  setPeriod: (p: Period) => void
  t: ReturnType<typeof useT>
}

const PERIODS: Period[] = ['7D', '1M', '3M', 'ALL']

function now() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

export default function TopBar({ info, ticker, latest, period, setPeriod, t }: Props) {
  const ret = latest?.daily_return_simple ?? 0
  const retPct = (Math.abs(ret) * 100).toFixed(2)
  const isUp = ret >= 0
  const price = latest?.adj_close_price

  return (
    <div className="h-12 flex items-center px-5 gap-5 border-b border-white/[0.06] flex-shrink-0"
      style={{ background: 'rgba(6,10,20,0.6)' }}>

      {/* Identity */}
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="text-xl leading-none">{info.flag}</span>
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-bold text-white leading-none truncate">{info.name}</span>
            <span className="font-mono text-[10px] text-[#2d4560] hidden sm:block">{ticker}</span>
          </div>
          <div className="text-[9px] text-[#2d4560] uppercase tracking-wider mt-px">{info.sector}</div>
        </div>
      </div>

      {/* Price */}
      {price != null && (
        <>
          <div className="w-px h-5 bg-white/[0.07] flex-shrink-0" />
          <div className="flex items-baseline gap-2 flex-shrink-0">
            <span className="font-mono text-base font-bold text-white">${price.toFixed(2)}</span>
            <span className={clsx('font-mono text-xs font-semibold', isUp ? 'text-up' : 'text-down')}>
              {isUp ? '+' : '-'}{retPct}%
            </span>
          </div>
        </>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Market time */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 pulse-dot" />
        <span className="font-mono text-[10px] text-[#2d4560]">{now()} UTC-3</span>
      </div>

      <div className="w-px h-5 bg-white/[0.07] flex-shrink-0" />

      {/* Period selector */}
      <div className="flex gap-1 flex-shrink-0">
        {PERIODS.map(p => (
          <button key={p} onClick={() => setPeriod(p)}
            className={clsx('period-btn', period === p && 'active')}>
            {p === 'ALL' ? t.pAll : p}
          </button>
        ))}
      </div>
    </div>
  )
}
