import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useFund, usePod } from '@/data/useFund'
import { PortfolioChart } from '@/components/PortfolioChart'
import { TradesTable } from '@/components/TradesFeed'
import { PositionsTable } from '@/components/Positions'
import { Money, Pct, PodGlyph } from '@/components/ui'
import { formatCurrency } from '@/lib/formatters'

export function PodDetail() {
  const { id } = useParams()
  const pod = usePod(id)
  const fund = useFund()

  const podTrades = useMemo(
    () => fund.trades.filter((t) => t.podId === pod?.id).slice(0, 25),
    [fund.trades, pod?.id],
  )

  if (!pod) {
    return (
      <div className="py-20 text-center">
        <p className="label">Pod not found</p>
        <Link to="/pods" className="mt-3 inline-block underline underline-offset-4">← Back to pods</Link>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link to="/pods" className="text-2xs uppercase tracking-[0.14em] underline underline-offset-4">← All pods</Link>
        <Link to="/leaderboard" className="text-2xs uppercase tracking-[0.14em] underline underline-offset-4">Leaderboard →</Link>
      </div>

      {/* header */}
      <header className="card flex flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <PodGlyph tint={pod.tint} label={pod.name} size={44} />
          <div>
            <h1 className="font-serif text-3xl">{pod.code}: {pod.name}</h1>
            <p className="text-2xs uppercase tracking-[0.12em] text-faint">{pod.strategy} · {pod.assetClass}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="label">Live Net Worth</div>
          <div className="text-2xl num">{formatCurrency(pod.accountValue)}</div>
          <div className="text-sm"><Pct value={pod.totalReturn} /> all-time</div>
        </div>
      </header>

      {/* metric strip */}
      <div className="grid grid-cols-2 gap-px border border-rule bg-rule md:grid-cols-6">
        <Cell label="Realized P&L"><Money value={pod.realizedPnl} signed /></Cell>
        <Cell label="Unrealized P&L"><Money value={pod.unrealizedPnl} signed /></Cell>
        <Cell label="Net P&L"><Money value={pod.totalPnl} signed /></Cell>
        <Cell label="Cash">{formatCurrency(pod.cash)}</Cell>
        <Cell label="Fees">{formatCurrency(pod.fees)}</Cell>
        <Cell label="Allocated">{formatCurrency(pod.allocatedCapital)}</Cell>
        <Cell label="Sharpe">{pod.sharpe.toFixed(2)}</Cell>
        <Cell label="Max Drawdown"><span className="neg">{(pod.maxDrawdown * 100).toFixed(1)}%</span></Cell>
        <Cell label="Win Rate">{(pod.winRate * 100).toFixed(0)}%</Cell>
        <Cell label="Avg Leverage">{pod.avgLeverage.toFixed(2)}x</Cell>
        <Cell label="Biggest Win"><span className="pos">+{formatCurrency(pod.biggestWin)}</span></Cell>
        <Cell label="Biggest Loss"><span className="neg">{formatCurrency(pod.biggestLoss)}</span></Cell>
      </div>

      <p className="card-soft px-5 py-3 text-xs leading-relaxed text-ink/90">{pod.description}</p>

      {/* chart (this pod highlighted vs others faintly via single line) */}
      <div>
        <h2 className="label-strong mb-2">Account Value</h2>
        <PortfolioChart pods={fund.pods} visible={[pod.id]} height={300} />
      </div>

      {/* traders */}
      <div>
        <h2 className="label-strong mb-2">Traders</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {pod.traders.map((t) => (
            <div key={t.id} className="card-soft px-3 py-3">
              <div className="flex items-center gap-2">
                <PodGlyph tint={t.tint} label={t.name} size={28} />
                <div>
                  <div className="text-xs font-semibold">{t.name}</div>
                  <div className="text-2xs text-faint uppercase tracking-[0.1em]">{t.role}</div>
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between text-2xs">
                <span className="text-faint uppercase tracking-[0.08em]">Live P&L</span>
                <Money value={t.livePnl} signed />
              </div>
              <div className="mt-1 flex items-center justify-between text-2xs">
                <span className="text-faint uppercase tracking-[0.08em]">Trades</span>
                <span className="num">{t.trades}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* positions */}
      <div>
        <h2 className="label-strong mb-2">Active Positions</h2>
        <div className="border border-rule">
          <PositionsTable positions={pod.positions} />
        </div>
      </div>

      {/* recent trades */}
      <div>
        <h2 className="label-strong mb-2">Recent Trades</h2>
        <div className="border border-rule">
          <TradesTable trades={podTrades} />
        </div>
      </div>
    </div>
  )
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-panel px-3 py-2.5">
      <div className="label">{label}</div>
      <div className="mt-0.5 text-sm num">{children}</div>
    </div>
  )
}
