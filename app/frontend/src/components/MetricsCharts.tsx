import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'
import type { DayMetric } from '../types'
import type { useT } from '../i18n'
import { format } from 'date-fns'

interface Props { data: DayMetric[]; t: ReturnType<typeof useT> }

const TOOLTIP_STYLE = {
  backgroundColor: 'rgba(4,12,26,0.98)',
  border: '1px solid rgba(59,130,246,0.25)',
  borderRadius: 8,
  padding: '8px 12px',
  fontSize: 11,
  fontFamily: 'JetBrains Mono, monospace',
  color: '#94a3b8',
}

function ChartWrapper({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-white/[0.05]">
        <span className="text-xs font-semibold text-[#7b9bc0] uppercase tracking-wider">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

export default function MetricsCharts({ data, t }: Props) {
  const chartData = data.map(d => ({
    date: format(new Date(d.trade_date), 'MMM d'),
    vol: d.volatility_30d_pct != null ? +d.volatility_30d_pct.toFixed(2) : null,
    ret: d.daily_return_simple != null ? +(d.daily_return_simple * 100).toFixed(2) : null,
  }))

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Volatility */}
      <ChartWrapper title={t.volatility}>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" tick={{ fill: '#3d5475', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#3d5475', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#64748b' }} formatter={(v: number) => [`${v}%`, t.volatility]} />
            <Area type="monotone" dataKey="vol" stroke="#ef4444" strokeWidth={1.5} fill="url(#volGrad)" dot={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </ChartWrapper>

      {/* Daily Return */}
      <ChartWrapper title={t.dailyRet}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="date" tick={{ fill: '#3d5475', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#3d5475', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#64748b' }} formatter={(v: number) => [`${v.toFixed(2)}%`, t.dailyRet]} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
            <Bar dataKey="ret" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={(entry.ret ?? 0) >= 0 ? 'rgba(16,185,129,0.7)' : 'rgba(239,68,68,0.7)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartWrapper>
    </div>
  )
}
