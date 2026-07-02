import clsx from 'clsx'
import type { DayMetric } from '../types'
import type { useT } from '../i18n'

interface Props { latest: DayMetric; t: ReturnType<typeof useT> }

interface CardProps {
  label: string
  value: string
  sub: string
  badge?: string
  badgeUp?: boolean | null   // true=green, false=red, null=neutral
  delta?: string
  deltaUp?: boolean | null
}

function KpiCard({ label, value, sub, badge, badgeUp, delta, deltaUp }: CardProps) {
  const badgeColor =
    badgeUp === true  ? 'rgba(16,185,129,0.15)' :
    badgeUp === false ? 'rgba(244,63,94,0.15)'  : 'rgba(255,255,255,0.07)'
  const badgeText =
    badgeUp === true  ? '#6ee7b7' :
    badgeUp === false ? '#fda4af' : 'var(--text-secondary)'

  return (
    <div className="glass glass-hover rounded-xl p-5 relative overflow-hidden cursor-default">
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px opacity-50"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(59,130,246,0.6), transparent)' }} />

      {/* Label */}
      <div className="label mb-3" style={{ fontSize: '11px' }}>{label}</div>

      {/* Main value */}
      <div className="kpi-value mb-2">{value}</div>

      {/* Sub info row */}
      <div className="flex items-center gap-2 flex-wrap">
        {badge && (
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-md"
            style={{ background: badgeColor, color: badgeText }}
          >
            {badge}
          </span>
        )}
        {delta && (
          <span className={clsx('font-mono text-sm font-semibold', deltaUp === true ? 'text-up' : deltaUp === false ? 'text-down' : 'text-[#7a96b8]')}>
            {delta}
          </span>
        )}
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{sub}</span>
      </div>
    </div>
  )
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function KpiGrid({ latest, t }: Props) {
  const ret   = latest.daily_return_simple ?? 0
  const retPct = ret * 100
  const vol   = latest.volatility_30d_pct
  const sma7  = latest.sma_7d
  const rv    = latest.relative_volume
  const close = latest.adj_close_price

  const volBadge = vol != null
    ? (vol > 30 ? t.volHigh : vol > 15 ? t.volMid : t.volLow)
    : undefined
  const volUp = vol != null ? (vol > 30 ? false : vol > 15 ? null : true) : null

  const rvBadge = rv != null
    ? (rv > 1.5 ? t.volElevated : rv < 0.7 ? t.volMuted : t.volNormal)
    : undefined
  const rvUp = rv != null ? (rv > 1.5 ? true : rv < 0.7 ? false : null) : null

  const smaDelta = sma7 != null
    ? (close > sma7
        ? `▲ +${((close / sma7 - 1) * 100).toFixed(1)}% ${t.smaAbove}`
        : `▼ ${((close / sma7 - 1) * 100).toFixed(1)}% ${t.smaBelow}`)
    : undefined

  return (
    <div className="grid grid-cols-4 gap-4">
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
        badge={volBadge}
        badgeUp={volUp}
      />
      <KpiCard
        label={t.sma7}
        value={sma7 != null ? `$${fmt(sma7)}` : '—'}
        sub={t.sma7Label}
        delta={smaDelta}
        deltaUp={sma7 != null ? close > sma7 : null}
      />
      <KpiCard
        label={t.relVol}
        value={rv != null ? `${rv.toFixed(2)}×` : '—'}
        sub={t.vs30dAvg}
        badge={rvBadge}
        badgeUp={rvUp}
      />
    </div>
  )
}
