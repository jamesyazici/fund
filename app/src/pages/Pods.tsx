import { Link } from 'react-router-dom'
import { useFund } from '@/data/useFund'
import { PortfolioChart } from '@/components/PortfolioChart'
import { Money, NoData, Pct, PodGlyph } from '@/components/ui'
import { formatCurrency } from '@/lib/formatters'

export function Pods() {
  const { pods } = useFund()

  if (pods.length === 0) {
    return (
      <div>
        <h1 className="font-serif text-4xl">Pods</h1>
        <NoData title="No pods yet" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <header className="border-b border-rule pb-3">
        <h1 className="font-serif text-4xl">Pods</h1>
        <p className="mt-1 text-xs text-faint">
          Each pod is a strategy team trading one account. Select a pod for its live net worth, realized P&amp;L,
          recent trades, positions and roster.
        </p>
      </header>

      <PortfolioChart pods={pods} height={320} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {pods.map((p) => (
          <Link key={p.id} to={`/pods/${p.code}`} className="card flex flex-col gap-3 px-4 py-4 hover:bg-paper">
            <div className="flex items-center gap-3">
              <PodGlyph tint={p.tint} label={p.name} size={36} />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{p.code}: {p.name}</div>
                <div className="text-2xs text-faint">{p.strategy}</div>
              </div>
            </div>
            <p className="text-2xs leading-relaxed text-ink/80 line-clamp-3">{p.description}</p>
            <div className="mt-auto grid grid-cols-2 gap-2 border-t border-line pt-3 text-2xs">
              <KV k="Net Worth" v={formatCurrency(p.accountValue)} />
              <KV k="Total Return" v={<Pct value={p.totalReturn} />} />
              <KV k="Realized" v={<Money value={p.realizedPnl} signed />} />
              <KV k="Unrealized" v={<Money value={p.unrealizedPnl} signed />} />
              <KV k="Sharpe" v={p.sharpe.toFixed(2)} />
              <KV k="Traders" v={String(p.traders.length)} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-faint uppercase tracking-[0.08em]">{k}</span>
      <span className="num">{v}</span>
    </div>
  )
}
