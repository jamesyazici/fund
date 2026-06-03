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
    <div className="text-center py-10">
      <p className="text-sm text-zinc-500 uppercase tracking-widest mb-1">Total AUM</p>
      <p className="text-5xl font-extrabold text-zinc-900 dark:text-white tabular-nums">
        {formatCompact(totalStarting)}
      </p>
      <p className="text-sm text-zinc-500 dark:text-zinc-600 mt-1">across {pods.length} pod{pods.length !== 1 ? 's' : ''}</p>
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
    <div className="space-y-10">
      <TotalAUM pods={pods} />

      <section>
        <h2 className="section-heading">
          Pods
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {pods.map((pod) => (
            <PodCard key={pod.id} pod={pod} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-heading">
          Recent Trades (Fund-Wide)
        </h2>
        <TradeBlotter limit={20} />
      </section>
    </div>
  )
}
