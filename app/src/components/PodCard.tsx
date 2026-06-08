import { Link } from 'react-router-dom'
import { useNavHistory } from '@/hooks/useNavHistory'
import { useMetrics } from '@/hooks/useMetrics'
import { formatCompact, formatPct } from '@/lib/formatters'
import { ASSET_CLASS_LABELS } from '@/lib/metrics'
import { cn } from '@/lib/cn'
import type { Pod } from '@/types/db'
import type { LivePodSnapshot } from '@/hooks/useLiveSnapshots'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { ArrowUpRight, Radio } from 'lucide-react'

interface PodCardProps {
  pod: Pod
  live?: LivePodSnapshot
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

export function PodCard({ pod, live }: PodCardProps) {
  const { data: history } = useNavHistory(pod.id, 1)
  const { data: metrics } = useMetrics(pod.id)
  const latest = history?.[history.length - 1]
  const nav = live?.nav ?? latest?.nav ?? pod.allocated_capital
  const totalReturn = live?.total_return ?? (pod.allocated_capital ? (Number(nav) / pod.allocated_capital) - 1 : null)
  const dayReturn = live?.daily_return ?? latest?.daily_return ?? null
  const positive = (totalReturn ?? dayReturn ?? 0) >= 0
  const returnLabel = totalReturn != null ? formatPct(totalReturn) : dayReturn != null ? formatPct(dayReturn) : '0.00%'

  return (
    <Link
      to={`/pod/${pod.id}`}
      className="group block overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-zinc-400 hover:shadow-lg dark:border-white/10 dark:bg-[#0a0d0c] dark:hover:border-[#7cffb2]/35"
    >
      <div className="border-b border-zinc-100 bg-zinc-50 px-4 py-2 dark:border-white/10 dark:bg-white/[0.03]">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-500">
            {ASSET_CLASS_LABELS[pod.asset_class] ?? pod.asset_class}
          </span>
          <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em]', live?.live ? 'border-emerald-500/30 text-emerald-600 dark:text-[#7cffb2]' : 'border-zinc-300 text-zinc-500 dark:border-zinc-700')}>
            <Radio className="h-3 w-3" />
            {live?.live ? 'live' : 'snapshot'}
          </span>
        </div>
      </div>
      <div className="p-4">
        <div className="mb-4 flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 font-black leading-tight text-zinc-950 dark:text-white">
              {pod.name}
            </h3>
            <p className="mt-1 line-clamp-1 text-xs text-zinc-500">{pod.description || pod.benchmark_symbol}</p>
          </div>
          <ArrowUpRight className="h-4 w-4 shrink-0 text-zinc-400 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 dark:text-zinc-500" />
        </div>

        <Sparkline podId={pod.id} />

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">NAV</p>
            <p className="mt-1 text-lg font-black text-zinc-950 tabular-nums dark:text-white">{formatCompact(nav)}</p>
          </div>
          <div className={cn('rounded-lg border px-3 py-2', positive ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-[#7cffb2]/25 dark:bg-[#7cffb2]/10 dark:text-[#7cffb2]' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-400/25 dark:bg-red-400/10 dark:text-red-300')}>
            <p className="text-[11px] uppercase tracking-[0.14em] opacity-70">Return</p>
            <p className="mt-1 text-lg font-black tabular-nums">{returnLabel}</p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Capital</p>
            <p className="mt-1 text-lg font-black text-zinc-950 tabular-nums dark:text-white">{formatCompact(pod.allocated_capital)}</p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Exposure</p>
            <p className="mt-1 text-lg font-black text-zinc-950 tabular-nums dark:text-white">{formatCompact(live?.gross_notional ?? 0)}</p>
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
