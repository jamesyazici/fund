import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { format } from 'date-fns'
import { useNotionalHistory, type LivePodSnapshot } from '@/hooks/useLiveSnapshots'
import { formatCurrency } from '@/lib/formatters'

interface PortfolioNotionalChartProps {
  podId: string
  live?: LivePodSnapshot
}

export function PortfolioNotionalChart({ podId, live }: PortfolioNotionalChartProps) {
  const { data: history, isLoading } = useNotionalHistory(podId, 390)
  const rows = history?.length
    ? history
    : live
      ? [{ timestamp: new Date().toISOString(), gross_notional: live.gross_notional, net_notional: live.net_notional }]
      : []

  const latest = rows[rows.length - 1]

  if (isLoading && !live) {
    return <div className="h-full w-full animate-pulse bg-black/[0.03]" />
  }

  return (
    <div className="relative h-full min-h-[520px] bg-white">
      <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2 font-mono text-[11px] font-black uppercase tracking-[0.12em]">
        Total Portfolio Notional Value
      </div>
      <div className="absolute left-2 top-2 z-10 flex border border-black bg-white font-mono text-xs font-black">
        <span className="border-r border-black bg-black px-2 py-1 text-white">$</span>
        <span className="px-2 py-1">%</span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 42, right: 96, bottom: 24, left: 48 }}>
          <CartesianGrid stroke="#d8d8d3" strokeWidth={1} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => format(new Date(value), 'MMM d HH:mm')}
            tick={{ fontFamily: 'monospace', fontSize: 10, fill: '#111' }}
            axisLine={{ stroke: '#111' }}
            tickLine={false}
            minTickGap={44}
          />
          <YAxis
            tickFormatter={(value) => `$${Number(value).toLocaleString()}`}
            tick={{ fontFamily: 'monospace', fontSize: 10, fill: '#111' }}
            axisLine={{ stroke: '#111' }}
            tickLine={false}
            width={72}
          />
          <Tooltip
            contentStyle={{
              border: '1px solid #111',
              borderRadius: 0,
              background: '#fff',
              fontFamily: 'monospace',
              fontSize: 11,
            }}
            labelFormatter={(value) => format(new Date(value as string), 'MMM d, HH:mm')}
            formatter={(value: number, name) => [formatCurrency(value), name === 'gross_notional' ? 'Gross notional' : 'Net notional']}
          />
          <Line type="monotone" dataKey="gross_notional" stroke="#111111" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="net_notional" stroke="#6577bd" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      {latest && (
        <div className="absolute right-5 top-[28%] space-y-2 font-mono text-[10px] font-black">
          <div className="flex items-center gap-1">
            <span className="inline-block h-5 w-5 rounded-full bg-black" />
            <span className="bg-black px-1.5 py-0.5 text-white">{formatCurrency(latest.gross_notional)}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="inline-block h-5 w-5 rounded-full bg-[#6577bd]" />
            <span className="bg-[#6577bd] px-1.5 py-0.5 text-white">{formatCurrency(latest.net_notional)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
