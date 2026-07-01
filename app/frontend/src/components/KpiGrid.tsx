import clsx from 'clsx'
import type { DayMetric } from '../types'
import type { useT } from '../i18n'

interface Props { latest: DayMetric; t: ReturnType<typeof useT> }

interface CardProps {
  label: string
  value: string
  sub: string
  delta?: string
  deltaUp?: boolean | null   // true=green, false=red, null=neutral
  border?: string
}

function KpiCard({ label, value, sub, delta, deltaUp, border }: CardProps) {
  const deltaColor = deltaUp === true ? 'text-up' : deltaUp === false ? 'text-down' : 'text-[#2d4560]'
  return (
    <div className={clsx('glass glass-hover rounded-lg p-4 cursor-default relative overflow-hidden', border)}>
      {/* Subtle top glow */}
      <div className="absolute top-0 left-0 right-0 h-px opacity-40"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(59,130,246,0.5), transparent)' }} />

      <div className="label mb-2.5">{label}</div>
      <div className="kpi-value mb-1.5">{value}</div>
      <div className="flex items-center gap-1.5">
        {delta && <span className={clsx('text-[11px] font-semibold font-mono', deltaColor)}>{delta}</span>}
        <span className="text-[10px] text-[#2d4560]">{sub}</span>
      </div>
    </div>
  )
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function KpiGrid({ latest, t }: Props) {
  const ret = latest.daily_return_simple ?? 0
  const retPct = (ret * 100)
  const vol = latest.volatility_30d_pct
  const sma7 = latest.sma_7d
  const rv = latest.relative_volume
  const close = latest.adj_close_price

  return (
    <div className="grid grid-cols-4 gap-3">
      <KpiCard
        label={t.lastClose}
        value={`$${fmt(close)}`}
        sub={t.dailyReturn}
        delta={`${ret >= 0 ? '▲ +' : '▼ '}${Math.abs(retPct).toFixed(2)}%`}
        deltaUp={ret >= 0}
      />
      <KpiCard
        label={t.vol30d}
        value={vol != null ? `${vol.toFixed(1)}%` : '—'}
        sub={t.annualized}
        delta={vol != null ? (vol > 30 ? '↑ High' : vol > 15 ? '→ Mid' : '↓ Low') : undefined}
        deltaUp={vol != null ? (vol > 30 ? false : vol > 15 ? null : true) : null}
      />
      <KpiCard
        label={t.sma7}
        value={sma7 != null ? `$${fmt(sma7)}` : '—'}
        sub="7-day moving avg"
        delta={sma7 != null ? (close > sma7 ? `▲ +${((close/sma7-1)*100).toFixed(1)}%` : `▼ ${((close/sma7-1)*100).toFixed(1)}%`) : undefined}
        deltaUp={sma7 != null ? close > sma7 : null}
      />
      <KpiCard
        label={t.relVol}
        value={rv != null ? `${rv.toFixed(2)}×` : '—'}
        sub={t.vs30dAvg}
        delta={rv != null ? (rv > 1.5 ? '↑ Elevated' : rv < 0.7 ? '↓ Muted' : '→ Normal') : undefined}
        deltaUp={rv != null ? (rv > 1.5 ? true : rv < 0.7 ? false : null) : null}
      />
    </div>
  )
}
