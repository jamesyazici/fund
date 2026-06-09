import { useFund } from '@/data/useFund'
import { cn } from '@/lib/cn'

// Wall-street style sliding stock tape under the navbar.
export function Ticker() {
  const { ticker } = useFund()
  const items = ticker.length ? ticker : []
  // duplicate the list so the marquee loops seamlessly (-50% translate)
  const loop = [...items, ...items]

  return (
    <div className="border-y border-rule bg-panel overflow-hidden">
      <div className="relative flex">
        <div className="ticker-track flex shrink-0 animate-ticker whitespace-nowrap">
          {loop.map((it, i) => {
            const up = it.changePct >= 0
            return (
              <span key={i} className="flex items-center gap-2 px-4 py-1.5 border-r border-line text-xs num">
                <span className="font-semibold">{it.symbol}</span>
                <span>{it.price.toFixed(2)}</span>
                <span className={cn('text-2xs', up ? 'pos' : 'neg')}>
                  {up ? '▲' : '▼'} {Math.abs(it.changePct).toFixed(2)}%
                </span>
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}
