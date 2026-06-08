import { useState } from 'react'
import { usePods } from '@/hooks/usePods'
import { TradeBlotter } from '@/components/TradeBlotter'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'

export function Trades() {
  const [selectedPod, setSelectedPod] = useState<string>('')
  const { data: pods } = usePods()
  useRealtimeTrades(selectedPod || undefined)

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-zinc-200/80 bg-white/80 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/[0.04]">
        <div className="flex flex-wrap gap-4 items-end justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">
              Execution audit
            </p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-zinc-950 dark:text-white">
              All Trades
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              Filter by pod and review every trade with trader attribution.
            </p>
          </div>
          <select
            value={selectedPod}
            onChange={(e) => setSelectedPod(e.target.value)}
            className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-white/10 dark:bg-zinc-950/60 dark:text-zinc-200"
          >
            <option value="">All Pods</option>
            {pods?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <TradeBlotter podId={selectedPod || undefined} limit={500} />
    </div>
  )
}
