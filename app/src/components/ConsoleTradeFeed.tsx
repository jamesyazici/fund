import { useTrades } from '@/hooks/useTrades'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/cn'

interface ConsoleTradeFeedProps {
  podId?: string
  limit?: number
}

function compactTime(value: string) {
  return new Date(value).toLocaleString('en-US', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function ConsoleTradeFeed({ podId, limit = 26 }: ConsoleTradeFeedProps) {
  const { data: trades, isLoading, error } = useTrades({ podId, limit })
  useRealtimeTrades(podId)

  return (
    <aside className="flex min-h-0 flex-col border-l border-black bg-[#f6f6f3]">
      <div className="grid grid-cols-4 border-b border-black text-[10px] font-black uppercase tracking-[0.08em]">
        <div className="border-r border-black bg-black px-2 py-2 text-white">Completed Trades</div>
        <div className="border-r border-black px-2 py-2">Trader Chat</div>
        <div className="border-r border-black px-2 py-2">Positions</div>
        <div className="px-2 py-2">Readme.txt</div>
      </div>
      <div className="border-b border-black px-2 py-1 font-mono text-[11px]">
        <span className="font-black">FILTER:</span>{' '}
        <span className="inline-block border border-black bg-white px-1">ALL PODS ▾</span>
        <span className="float-right">Showing last {trades?.length ?? 0} trades</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading && <div className="p-3 font-mono text-xs">Loading ledger...</div>}
        {error && <div className="p-3 font-mono text-xs text-red-700">Failed to load trades.</div>}
        {!isLoading && !error && !trades?.length && (
          <div className="p-3 font-mono text-xs">No completed trades yet.</div>
        )}
        {trades?.map((trade) => {
          const isBuy = trade.side === 'buy'
          const qty = Number(trade.filled_qty ?? trade.quantity ?? 0)
          const notional = trade.notional ?? (trade.price != null ? Math.abs(qty * trade.price) : null)
          return (
            <article key={trade.id} className="border-b border-black/20 px-3 py-2 font-mono text-[11px] leading-5">
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0">
                  <span className="font-black text-indigo-700">{trade.traders?.display_name ?? 'Trader'}</span>{' '}
                  completed a{' '}
                  <span className={cn('font-black', isBuy ? 'text-emerald-700' : 'text-red-700')}>
                    {trade.side}
                  </span>{' '}
                  trade on{' '}
                  <span className="font-black">{trade.symbol}</span>
                </p>
                <span className="shrink-0 text-[10px] text-zinc-500">{compactTime(trade.executed_at)}</span>
              </div>
              <p>Price: {formatCurrency(trade.price)} </p>
              <p>Quantity: {qty.toLocaleString()}</p>
              <p>Notional: {formatCurrency(notional)}</p>
              <p>Book: {trade.asset_class.replace('_', ' ')}</p>
              <p>
                NET P&L:{' '}
                <span className={cn('font-black', isBuy ? 'text-emerald-700' : 'text-red-700')}>
                  {trade.status || 'recorded'}
                </span>
              </p>
            </article>
          )
        })}
      </div>
    </aside>
  )
}
