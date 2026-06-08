import { useParams, Link } from 'react-router-dom'
import { usePod } from '@/hooks/usePods'
import { MemberList } from '@/components/MemberList'
import { NavChart } from '@/components/NavChart'
import { PositionsTable } from '@/components/PositionsTable'
import { TradeBlotter } from '@/components/TradeBlotter'
import { MetricsPanel } from '@/components/MetricsPanel'
import { ASSET_CLASS_COLORS, ASSET_CLASS_LABELS } from '@/lib/metrics'
import { formatCompact, formatCurrency, formatDate, formatPct } from '@/lib/formatters'
import { useRealtimeNav } from '@/hooks/useRealtimeTrades'
import { useLivePodSnapshot } from '@/hooks/useLiveSnapshots'
import { cn } from '@/lib/cn'
import { Radio } from 'lucide-react'

export function PodDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: pod, isLoading, error } = usePod(id ?? '')
  const { data: live } = useLivePodSnapshot(id ?? '')
  useRealtimeNav(id ?? '')

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-24 rounded-2xl bg-zinc-100 dark:bg-white/5" />
        <div className="h-64 rounded-2xl bg-zinc-100 dark:bg-white/5" />
      </div>
    )
  }

  if (error || !pod) {
    return (
      <div className="py-20 text-center text-zinc-500">
        <p>Pod not found.</p>
        <Link to="/" className="mt-4 inline-block text-indigo-600 dark:text-indigo-400 hover:underline text-sm">
          ← Back to overview
        </Link>
      </div>
    )
  }

  const accentColor = ASSET_CLASS_COLORS[pod.asset_class] ?? '#6366f1'
  const totalReturn = live?.total_return ?? null
  const positive = (totalReturn ?? 0) >= 0

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white dark:border-white/10 dark:bg-[#0d1014]">
        <div className="h-1.5" style={{ backgroundColor: accentColor }} />
        <div className="p-6">
          <div className="flex flex-wrap gap-3 items-start justify-between mb-4">
            <div>
              <Link to="/" className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 mb-1 inline-block">
                ← Fund Overview
              </Link>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">{pod.name}</h1>
              <span
                className="mt-1 inline-block text-xs px-2 py-0.5 rounded-full"
                style={{ background: `${accentColor}25`, color: accentColor }}
              >
                {ASSET_CLASS_LABELS[pod.asset_class] ?? pod.asset_class}
              </span>
              {pod.description && (
                <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 max-w-xl">{pod.description}</p>
              )}
            </div>
            <div className="text-sm text-zinc-500 space-y-1 text-right">
              <p className="flex items-center justify-end gap-1.5 text-emerald-600 dark:text-emerald-300">
                <Radio className="h-3.5 w-3.5" />
                {live?.live ? 'Live Alpaca marks' : 'Snapshot fallback'}
              </p>
              <p>Benchmark: <span className="text-zinc-700 dark:text-zinc-300 font-mono">{pod.benchmark_symbol}</span></p>
              <p>Inception: <span className="text-zinc-700 dark:text-zinc-300">{formatDate(pod.inception_date)}</span></p>
            </div>
          </div>
          <div className="mb-5 grid grid-cols-2 gap-2 md:grid-cols-4">
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/[0.04]">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Live NAV</p>
              <p className="mt-1 text-xl font-black tabular-nums text-zinc-950 dark:text-white">{formatCompact(live?.nav ?? pod.allocated_capital)}</p>
            </div>
            <div className={cn('rounded-lg border p-3', positive ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-200' : 'border-red-200 bg-red-50 text-red-800 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200')}>
              <p className="text-xs uppercase tracking-wide opacity-70">Return</p>
              <p className="mt-1 text-xl font-black tabular-nums">{formatPct(totalReturn)}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/[0.04]">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Gross notional</p>
              <p className="mt-1 text-xl font-black tabular-nums text-zinc-950 dark:text-white">{formatCurrency(live?.gross_notional ?? 0, 0)}</p>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/[0.04]">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Cash</p>
              <p className="mt-1 text-xl font-black tabular-nums text-zinc-950 dark:text-white">{formatCurrency(live?.cash ?? null, 0)}</p>
            </div>
          </div>
          <MemberList podId={pod.id} />
        </div>
      </div>

      {/* NAV Chart */}
      <section>
        <h2 className="section-heading">NAV History</h2>
        <div className="rounded-lg border border-zinc-200 bg-white dark:border-white/10 dark:bg-[#0d1014] p-5">
          <NavChart podId={pod.id} startingCapital={Number(pod.allocated_capital)} liveNav={live?.nav} />
        </div>
      </section>

      {/* Risk / Performance Metrics */}
      <section>
        <h2 className="section-heading">Risk & Performance</h2>
        <MetricsPanel podId={pod.id} />
      </section>

      {/* Open Positions */}
      <section>
        <h2 className="section-heading">Open Positions</h2>
        <PositionsTable podId={pod.id} livePositions={live?.positions} />
      </section>

      {/* Trade Blotter */}
      <section>
        <h2 className="section-heading">Trade Blotter</h2>
        <TradeBlotter podId={pod.id} limit={100} />
      </section>
    </div>
  )
}
