import { Link } from 'react-router-dom'
import { useNavHistory } from '@/hooks/useNavHistory'
import { useMetrics } from '@/hooks/useMetrics'
import { formatCompact, formatPct } from '@/lib/formatters'
import { ASSET_CLASS_COLORS, ASSET_CLASS_LABELS } from '@/lib/metrics'
import { cn } from '@/lib/cn'
import type { Pod } from '@/types/db'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'

interface PodCardProps {
  pod: Pod
}

function Sparkline({ podId }: { podId: string }) {
  const { data: history } = useNavHistory(podId, 30)
  if (!history?.length) return <div className="h-10" />
  const data = history.map((r) => ({ v: Number(r.nav) }))
  const first = data[0].v
  const last = data[data.length - 1].v
  const color = last >= first ? '#34d399' : '#f87171'
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke={color} dot={false} strokeWidth={1.5} />
        <Tooltip contentStyle={{ display: 'none' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function PodCard({ pod }: PodCardProps) {
  const { data: history } = useNavHistory(pod.id, 1)
  const { data: metrics } = useMetrics(pod.id)
  const accentColor = ASSET_CLASS_COLORS[pod.asset_class] ?? '#6366f1'

  const latest = history?.[history.length - 1]
  const nav = latest?.nav ?? pod.allocated_capital
  const dayReturn = latest?.daily_return ?? null
  const positive = (dayReturn ?? 0) >= 0
  const returnLabel = dayReturn != null ? formatPct(Math.abs(dayReturn)) : '0.0%'

  return (
    <Link
      to={`/pod/${pod.id}`}
      className="group block overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-lg dark:border-white/10 dark:bg-[#0d1014] dark:hover:border-white/20"
    >
      <div className="p-4">
        <div className="mb-4 flex items-start gap-3">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-black text-white"
            style={{ backgroundColor: accentColor }}
          >
            {pod.name.slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 font-black leading-tight text-zinc-950 dark:text-white">
              {pod.name}
            </h3>
            <span className="mt-1 inline-flex rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-600 dark:bg-white/[0.06] dark:text-zinc-300">
              {ASSET_CLASS_LABELS[pod.asset_class] ?? pod.asset_class}
            </span>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-xs text-zinc-500">NAV</p>
            <p className="text-base font-black text-zinc-950 dark:text-white tabular-nums">{formatCompact(nav)}</p>
          </div>
        </div>

        <Sparkline podId={pod.id} />

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className={cn('rounded-xl px-3 py-2 text-center font-bold', positive ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300' : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300')}>
            <p className="text-xs opacity-70">{positive ? 'Up' : 'Down'}</p>
            <p className="text-lg tabular-nums">{returnLabel}</p>
          </div>
          <div className="rounded-xl bg-blue-50 px-3 py-2 text-center font-bold text-blue-700 dark:bg-blue-500/10 dark:text-blue-300">
            <p className="text-xs opacity-70">Capital</p>
            <p className="text-lg tabular-nums">{formatCompact(pod.allocated_capital)}</p>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-zinc-100 pt-3 text-center dark:border-white/10">
          <div>
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Sharpe</p>
            <p className="text-sm font-semibold text-zinc-900 dark:text-white">
              {metrics?.sharpe != null ? metrics.sharpe.toFixed(2) : '—'}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Ann. Ret.</p>
            <p
              className={cn(
                'text-sm font-medium',
                (metrics?.annualized_return ?? 0) >= 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400',
              )}
            >
              {metrics?.annualized_return != null ? formatPct(metrics.annualized_return) : '—'}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">β</p>
            <p className="text-sm font-semibold text-zinc-900 dark:text-white">
              {metrics?.beta != null ? metrics.beta.toFixed(2) : '—'}
            </p>
          </div>
        </div>
      </div>
    </Link>
  )
}
