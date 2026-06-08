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
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#0d1014] sm:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-blue-600">
            Featured fund market
          </p>
          <h1 className="mt-2 max-w-3xl text-2xl font-black tracking-tight text-zinc-950 dark:text-white sm:text-4xl">
            Which RQFC pod is leading the desk right now?
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Live NAV, capital, and execution activity across all trading pods.
          </p>
        </div>
        <div className="grid min-w-72 grid-cols-2 gap-2">
          <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-white/[0.04]">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Total AUM</p>
            <p className="mt-1 text-3xl font-extrabold text-zinc-950 dark:text-white tabular-nums">
              {formatCompact(totalStarting)}
            </p>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-white/[0.04]">
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
            <h2 className="text-xl font-black text-zinc-950 dark:text-white">Featured pods</h2>
            <p className="text-sm text-zinc-500">Market-style cards for each strategy desk.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {pods.map((pod) => (
            <PodCard key={pod.id} pod={pod} />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-xl font-black text-zinc-950 dark:text-white">Live activity</h2>
          <p className="text-sm text-zinc-500">Execution feed with trader attribution.</p>
        </div>
        <TradeBlotter limit={20} />
      </section>
    </div>
  )
}
