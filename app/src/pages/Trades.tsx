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
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-900 dark:text-white">All Trades</h1>
        <select
          value={selectedPod}
          onChange={(e) => setSelectedPod(e.target.value)}
          className="bg-white border border-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:border-white/10 dark:text-zinc-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Pods</option>
          {pods?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      <TradeBlotter podId={selectedPod || undefined} limit={500} />
    </div>
  )
}
