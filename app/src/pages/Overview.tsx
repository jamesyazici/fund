import { usePods } from '@/hooks/usePods'
import { PodCard } from '@/components/PodCard'
import { TradeBlotter } from '@/components/TradeBlotter'
import { formatCompact, formatCurrency, formatPct } from '@/lib/formatters'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { cn } from '@/lib/cn'
import { CircleDollarSign, Radio, TrendingDown, TrendingUp, WalletCards } from 'lucide-react'

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
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-[#070908] text-white shadow-[0_24px_80px_rgba(0,0,0,.28)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 bg-[#0b0f0d] px-4 py-2">
        <div className="flex flex-wrap items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
          <span className="flex items-center gap-1.5 text-[#7cffb2]">
            <Radio className="h-3.5 w-3.5" />
            {liveCount}/{pods.length} Live
          </span>
          <span>Student fund transparency</span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
        <span className="rounded-full border border-zinc-700 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
          Read only
        </span>
      </div>
      <div className="grid gap-5 p-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(380px,.9fr)] sm:p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-[#7cffb2]">
            RQFC live transparency
          </p>
          <h1 className="mt-3 max-w-4xl text-3xl font-black tracking-tight text-white sm:text-5xl">
            Live fund capital, positions, and trades.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">
            A public viewing surface for students to follow what the fund owns, how capital is allocated, and what orders were recorded.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-zinc-800 bg-[#0d1210] p-4">
            <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.16em] text-zinc-500">
              <WalletCards className="h-3.5 w-3.5" />
              Live NAV
            </p>
            <p className="mt-2 text-3xl font-extrabold text-white tabular-nums">
              {formatCompact(totalNav)}
            </p>
          </div>
          <div className={cn('rounded-lg border p-4', positive ? 'border-[#7cffb2]/30 bg-[#7cffb2]/10 text-[#7cffb2]' : 'border-red-400/30 bg-red-400/10 text-red-300')}>
            <p className="text-xs uppercase tracking-wide opacity-70">Since inception</p>
            <p className="mt-1 flex items-center gap-2 text-3xl font-extrabold tabular-nums">
              {positive ? <TrendingUp className="h-6 w-6" /> : <TrendingDown className="h-6 w-6" />}
              {formatPct(totalReturn)}
            </p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-[#0d1210] p-4">
            <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.16em] text-zinc-500">
              <CircleDollarSign className="h-3.5 w-3.5" />
              Gross notional
            </p>
            <p className="mt-2 text-xl font-extrabold text-white tabular-nums">{formatCurrency(grossNotional, 0)}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-[#0d1210] p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Allocated</p>
            <p className="mt-2 text-xl font-extrabold text-white tabular-nums">{formatCurrency(totalStarting, 0)}</p>
          </div>
        </div>
      </div>
    </section>
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

      <section>
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-xl font-black text-zinc-950 dark:text-white">Fund modules</h2>
            <p className="text-sm text-zinc-500">Live capital and exposure by strategy desk.</p>
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
          <h2 className="text-xl font-black text-zinc-950 dark:text-white">Recorded transactions</h2>
          <p className="text-sm text-zinc-500">A public tape of fund trades as they are logged.</p>
        </div>
        <TradeBlotter limit={20} />
      </section>
    </div>
  )
}
