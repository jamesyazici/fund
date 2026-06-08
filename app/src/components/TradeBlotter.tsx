import { useTrades } from '@/hooks/useTrades'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { cn } from '@/lib/cn'
import type { Trade } from '@/types/db'

interface TradeBlotterProps {
  podId?: string
  limit?: number
}

function TradeRow({ trade }: { trade: Trade }) {
  const isBuy = trade.side === 'buy'
  const traderName = trade.traders?.display_name ?? 'Unknown'
  return (
    <tr className="border-b border-zinc-100 transition-colors hover:bg-zinc-50 dark:border-white/5 dark:hover:bg-[#101612]">
      <td className="py-3 px-3 font-mono text-[11px] uppercase tracking-[0.08em] text-zinc-500 dark:text-zinc-500 whitespace-nowrap">
        {formatDateTime(trade.executed_at)}
      </td>
      <td className="py-3 px-3">
        <span
          className={cn(
            'inline-flex min-w-14 justify-center rounded-md border px-2.5 py-1 text-[11px] font-black uppercase tracking-[0.14em]',
            isBuy
              ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-[#7cffb2]'
              : 'border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-300',
          )}
        >
          {trade.side}
        </span>
      </td>
      <td className="py-3 px-3 font-mono text-base font-black text-zinc-950 dark:text-white">
        {trade.symbol}
      </td>
      <td className="py-3 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
        {Number(trade.quantity).toLocaleString()}
      </td>
      <td className="py-3 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
        {formatCurrency(trade.price)}
      </td>
      <td className="py-3 px-3 text-right font-semibold text-zinc-950 dark:text-white tabular-nums">
        {formatCurrency(trade.notional)}
      </td>
      <td className="py-3 px-3 text-zinc-700 dark:text-zinc-200 whitespace-nowrap">
        {traderName}
      </td>
      <td className="py-3 px-3 text-xs text-zinc-500 capitalize whitespace-nowrap">
        {trade.asset_class.replace('_', ' ')}
      </td>
    </tr>
  )
}

export function TradeBlotter({ podId, limit = 50 }: TradeBlotterProps) {
  const { data: trades, isLoading, error } = useTrades({ podId, limit })
  useRealtimeTrades(podId)

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-zinc-100 dark:bg-white/5" />
        ))}
      </div>
    )
  }

  if (error || !trades?.length) {
    return (
      <p className="text-sm text-zinc-500 py-4">
        {error ? 'Failed to load trades.' : 'No trades yet.'}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#0a0d0c]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-white/10 dark:bg-[#0d1210]">
            <th className="py-2.5 px-3 text-left text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Recorded</th>
            <th className="py-2.5 px-3 text-left text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Side</th>
            <th className="py-2.5 px-3 text-left text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Ticker</th>
            <th className="py-2.5 px-3 text-right text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Qty</th>
            <th className="py-2.5 px-3 text-right text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Fill</th>
            <th className="py-2.5 px-3 text-right text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Notional</th>
            <th className="py-2.5 px-3 text-left text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Recorded by</th>
            <th className="py-2.5 px-3 text-left text-[11px] font-bold uppercase tracking-[0.16em] text-zinc-500">Book</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <TradeRow key={trade.id} trade={trade} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
