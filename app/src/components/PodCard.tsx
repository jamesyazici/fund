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

  return (
    <Link
      to={`/pod/${pod.id}`}
      className="group block overflow-hidden rounded-2xl border border-zinc-200/80 bg-white/85 shadow-sm backdrop-blur transition-all duration-200 hover:-translate-y-1 hover:border-zinc-300 hover:shadow-xl dark:border-white/10 dark:bg-white/[0.04] dark:hover:border-white/20"
    >
      <div className="h-1 w-full opacity-90" style={{ backgroundColor: accentColor }} />
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h3 className="font-semibold text-zinc-900 dark:text-white text-base leading-tight">
              {pod.name}
            </h3>
            <span
              className="inline-block mt-1 text-xs px-2 py-0.5 rounded-full"
              style={{ background: `${accentColor}25`, color: accentColor }}
            >
              {ASSET_CLASS_LABELS[pod.asset_class] ?? pod.asset_class}
            </span>
          </div>
          <div className="text-right shrink-0">
            <p className="text-lg font-bold text-zinc-900 dark:text-white tabular-nums">
              {formatCompact(nav)}
            </p>
            {dayReturn != null && (
              <p
                className={cn(
                  'text-xs font-medium',
                  dayReturn >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400',
                )}
              >
                {formatPct(dayReturn)} today
              </p>
            )}
          </div>
        </div>

        <Sparkline podId={pod.id} />

        <div className="mt-4 grid grid-cols-3 gap-2 border-t border-zinc-100 pt-3 text-center dark:border-white/10">
          <div className="rounded-xl bg-zinc-50 p-2 dark:bg-zinc-950/50">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Sharpe</p>
            <p className="text-sm font-medium text-zinc-900 dark:text-white">
              {metrics?.sharpe != null ? metrics.sharpe.toFixed(2) : '—'}
            </p>
          </div>
          <div className="rounded-xl bg-zinc-50 p-2 dark:bg-zinc-950/50">
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
          <div className="rounded-xl bg-zinc-50 p-2 dark:bg-zinc-950/50">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">β</p>
            <p className="text-sm font-medium text-zinc-900 dark:text-white">
              {metrics?.beta != null ? metrics.beta.toFixed(2) : '—'}
            </p>
          </div>
        </div>
      </div>
    </Link>
  )
}
