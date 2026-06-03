import { useParams, Link } from 'react-router-dom'
import { usePod } from '@/hooks/usePods'
import { MemberList } from '@/components/MemberList'
import { NavChart } from '@/components/NavChart'
import { PositionsTable } from '@/components/PositionsTable'
import { TradeBlotter } from '@/components/TradeBlotter'
import { MetricsPanel } from '@/components/MetricsPanel'
import { ASSET_CLASS_COLORS, ASSET_CLASS_LABELS } from '@/lib/metrics'
import { formatDate } from '@/lib/formatters'
import { useRealtimeNav } from '@/hooks/useRealtimeTrades'

export function PodDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: pod, isLoading, error } = usePod(id ?? '')
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

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="rounded-2xl border border-zinc-200 bg-white dark:border-white/10 dark:bg-zinc-900 overflow-hidden">
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
              <p>Benchmark: <span className="text-zinc-700 dark:text-zinc-300 font-mono">{pod.benchmark_symbol}</span></p>
              <p>Inception: <span className="text-zinc-700 dark:text-zinc-300">{formatDate(pod.inception_date)}</span></p>
            </div>
          </div>
          <MemberList podId={pod.id} />
        </div>
      </div>

      {/* NAV Chart */}
      <section>
        <h2 className="section-heading">NAV History</h2>
        <div className="rounded-2xl border border-zinc-200 bg-white dark:border-white/10 dark:bg-zinc-900 p-5">
          <NavChart podId={pod.id} startingCapital={Number(pod.allocated_capital)} />
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
        <PositionsTable podId={pod.id} />
      </section>

      {/* Trade Blotter */}
      <section>
        <h2 className="section-heading">Trade Blotter</h2>
        <TradeBlotter podId={pod.id} limit={100} />
      </section>
    </div>
  )
}
