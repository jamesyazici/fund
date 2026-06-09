import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Pod } from '@/data/types'
import { TINT_LINE } from '@/data/colors'
import { formatCurrency } from '@/lib/formatters'

interface Props {
  pods: Pod[]
  // pod ids to render; if undefined, render all
  visible?: string[]
  height?: number
}

// Live account value of every pod on one graph, labelled by pod.
export function PortfolioChart({ pods, visible, height = 420 }: Props) {
  const shown = visible ? pods.filter((p) => visible.includes(p.id)) : pods

  const data = useMemo(() => {
    const len = Math.max(0, ...pods.map((p) => p.nav.length))
    const rows: Record<string, number | string>[] = []
    for (let i = 0; i < len; i++) {
      const row: Record<string, number | string> = { t: pods[0]?.nav[i]?.t ?? String(i) }
      shown.forEach((p) => {
        if (p.nav[i]) row[p.id] = p.nav[i].value
      })
      rows.push(row)
    }
    return rows
  }, [pods, shown])

  const fmtAxis = (v: string) =>
    new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

  return (
    <div className="card-soft bg-panel">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 border-b border-line px-4 py-2.5">
        {shown.map((p) => (
          <span key={p.id} className="flex items-center gap-2 text-2xs uppercase tracking-[0.1em]">
            <span className="inline-block h-2.5 w-2.5 border border-rule" style={{ background: TINT_LINE[p.tint] }} />
            <span className="font-semibold">{p.code}: {p.name}</span>
            <span className={p.totalReturn >= 0 ? 'pos' : 'neg'}>
              {p.totalReturn >= 0 ? '+' : ''}{(p.totalReturn * 100).toFixed(2)}%
            </span>
          </span>
        ))}
      </div>
      <div className="px-2 pb-2 pt-3" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 18, bottom: 6, left: 6 }}>
            <CartesianGrid stroke="#e2dccd" vertical={false} />
            <XAxis
              dataKey="t"
              tickFormatter={fmtAxis}
              tick={{ fontSize: 10, fill: '#6b6658', fontFamily: 'monospace' }}
              stroke="#1a1916"
              minTickGap={48}
            />
            <YAxis
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 10, fill: '#6b6658', fontFamily: 'monospace' }}
              stroke="#1a1916"
              width={48}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                background: '#faf8f2',
                border: '1px solid #1a1916',
                borderRadius: 0,
                fontFamily: 'monospace',
                fontSize: 12,
              }}
              labelFormatter={(v) => new Date(v).toLocaleString('en-US', { dateStyle: 'medium' })}
              formatter={(value: number, name: string) => {
                const pod = pods.find((p) => p.id === name)
                return [formatCurrency(value), pod ? `${pod.code}: ${pod.name}` : name]
              }}
            />
            {shown.map((p) => (
              <Line
                key={p.id}
                type="monotone"
                dataKey={p.id}
                stroke={TINT_LINE[p.tint]}
                strokeWidth={1.6}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
