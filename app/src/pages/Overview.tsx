import { usePods } from '@/hooks/usePods'
import { PodCard } from '@/components/PodCard'
import { TradeBlotter } from '@/components/TradeBlotter'
import { formatCompact, formatCurrency, formatPct } from '@/lib/formatters'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { cn } from '@/lib/cn'
import { Activity, Radio, TrendingDown, TrendingUp } from 'lucide-react'

function TotalAUM({
  pods,
  livePods,
}: {
  pods: { id: string; allocated_capital: number }[]
  livePods: ReturnType<typeof useLiveSnapshots>['data']
}) {
  const totalStarting = pods.reduce((acc, p) => acc + p.allocated_capital, 0)
  const totalNav = livePods?.reduce((acc, p) => acc + Number(p.nav || 0), 0) ?? totalStarting
  const grossNotional = livePods?.reduce((acc, p) => acc + Number(p.gross_notional || 0), 0) ?? 0
  const liveCount = livePods?.filter((p) => p.live).length ?? 0
  const totalReturn = totalStarting ? totalNav / totalStarting - 1 : null
  const positive = (totalReturn ?? 0) >= 0

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#0b0d10]">
      <div className="border-b border-zinc-200 bg-zinc-50 px-4 py-2 dark:border-white/10 dark:bg-white/[0.03]">
        <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">
          <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-300">
            <Radio className="h-3.5 w-3.5" />
            {liveCount}/{pods.length} Live
          </span>
          <span>Public transparency feed</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
      <div className="grid gap-5 p-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(360px,.8fr)] sm:p-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-cyan-600 dark:text-cyan-300">
            RQFC live arena
          </p>
          <h1 className="mt-2 max-w-4xl text-3xl font-black tracking-tight text-zinc-950 dark:text-white sm:text-5xl">
            Fund transparency moves with the market.
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Live Alpaca marks refresh continuously. Supabase snapshots remain as fallback when a pod has no market feed.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-white/[0.04]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Live NAV</p>
            <p className="mt-1 text-3xl font-extrabold text-zinc-950 dark:text-white tabular-nums">
              {formatCompact(totalNav)}
            </p>
          </div>
          <div className={cn('rounded-lg border p-4', positive ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-200' : 'border-red-200 bg-red-50 text-red-800 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200')}>
            <p className="text-xs uppercase tracking-wide opacity-70">Since inception</p>
            <p className="mt-1 flex items-center gap-2 text-3xl font-extrabold tabular-nums">
              {positive ? <TrendingUp className="h-6 w-6" /> : <TrendingDown className="h-6 w-6" />}
              {formatPct(totalReturn)}
            </p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-white/[0.04]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Gross notional</p>
            <p className="mt-1 text-xl font-extrabold text-zinc-950 dark:text-white tabular-nums">{formatCurrency(grossNotional, 0)}</p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-white/10 dark:bg-white/[0.04]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">Allocated</p>
            <p className="mt-1 text-xl font-extrabold text-zinc-950 dark:text-white tabular-nums">{formatCurrency(totalStarting, 0)}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export function Overview() {
  const { data: pods, isLoading, error } = usePods()
  const { data: livePods } = useLiveSnapshots()
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
      <TotalAUM pods={pods} livePods={livePods} />

      {!!livePods?.length && (
        <section className="rounded-lg border border-zinc-200 bg-white dark:border-white/10 dark:bg-[#0d1014]">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-white/10">
            <div>
              <h2 className="font-black text-zinc-950 dark:text-white">Live leaderboard</h2>
              <p className="text-xs text-zinc-500">Ranked by live return, refreshed every 5 seconds.</p>
            </div>
            <Activity className="h-4 w-4 text-cyan-500" />
          </div>
          <div className="divide-y divide-zinc-100 dark:divide-white/10">
            {[...livePods]
              .sort((a, b) => (b.total_return ?? -Infinity) - (a.total_return ?? -Infinity))
              .slice(0, 6)
              .map((pod, index) => {
                const isPositive = (pod.total_return ?? 0) >= 0
                return (
                  <div key={pod.id} className="grid grid-cols-[2.5rem_minmax(0,1fr)_repeat(3,minmax(96px,140px))] items-center gap-3 px-4 py-3 text-sm max-md:grid-cols-[2rem_minmax(0,1fr)_auto]">
                    <div className="font-mono text-zinc-400">#{index + 1}</div>
                    <div className="min-w-0">
                      <p className="truncate font-bold text-zinc-950 dark:text-white">{pod.name}</p>
                      <p className="truncate text-xs text-zinc-500">{pod.asset_class} · {pod.live ? 'Alpaca live' : 'snapshot fallback'}</p>
                    </div>
                    <div className="text-right tabular-nums max-md:hidden">{formatCompact(pod.nav)}</div>
                    <div className="text-right tabular-nums max-md:hidden">{formatCompact(pod.gross_notional)}</div>
                    <div className={cn('text-right font-bold tabular-nums', isPositive ? 'text-emerald-600 dark:text-emerald-300' : 'text-red-600 dark:text-red-300')}>
                      {formatPct(pod.total_return)}
                    </div>
                  </div>
                )
              })}
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-xl font-black text-zinc-950 dark:text-white">Featured pods</h2>
            <p className="text-sm text-zinc-500">Market-style cards for each strategy desk.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {pods.map((pod) => (
            <PodCard key={pod.id} pod={pod} live={livePods?.find((live) => live.id === pod.id)} />
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
