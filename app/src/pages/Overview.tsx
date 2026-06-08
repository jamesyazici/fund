import { usePods } from '@/hooks/usePods'
import { PodCard } from '@/components/PodCard'
import { TradeBlotter } from '@/components/TradeBlotter'
import { formatCompact } from '@/lib/formatters'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'

function TotalAUM({ pods }: { pods: { id: string; allocated_capital: number }[] }) {
  const navData = pods.map((p) => {
    return { id: p.id, capital: p.allocated_capital }
  })

  const totalStarting = navData.reduce((acc, p) => acc + p.capital, 0)

  return (
    <div className="rounded-3xl border border-zinc-200/80 bg-white/80 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/[0.04] sm:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-3">
            Live fund dashboard
          </p>
          <h1 className="max-w-2xl text-4xl font-black tracking-tight text-zinc-950 dark:text-white sm:text-6xl">
            Pod performance, positions, and trades in one view.
          </h1>
        </div>
        <div className="grid min-w-64 grid-cols-2 gap-3">
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-zinc-950/50">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Total AUM</p>
            <p className="mt-1 text-3xl font-extrabold text-zinc-950 dark:text-white tabular-nums">
              {formatCompact(totalStarting)}
            </p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-zinc-950/50">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Pods</p>
            <p className="mt-1 text-3xl font-extrabold text-zinc-950 dark:text-white tabular-nums">
              {pods.length}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export function Overview() {
  const { data: pods, isLoading, error } = usePods()
  useRealtimeTrades()

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 rounded-2xl bg-zinc-100 dark:bg-white/5" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-52 rounded-2xl bg-zinc-100 dark:bg-white/5" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !pods) {
    return (
      <div className="py-20 text-center text-zinc-500">
        Failed to load fund data. Check your Supabase configuration.
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <TotalAUM pods={pods} />

      <section>
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-lg font-bold text-zinc-950 dark:text-white">Strategy Pods</h2>
            <p className="text-sm text-zinc-500">Capital, risk metrics, and latest NAV movement.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {pods.map((pod) => (
            <PodCard key={pod.id} pod={pod} />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-zinc-950 dark:text-white">Recent Trades</h2>
          <p className="text-sm text-zinc-500">Fund-wide execution feed with trader attribution.</p>
        </div>
        <TradeBlotter limit={20} />
      </section>
    </div>
  )
}
