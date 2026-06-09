import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useFund } from '@/data/useFund'
import { Money, NoData, Pct, PodGlyph } from '@/components/ui'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/cn'

type SortKey = 'livePnl' | 'realizedPnl' | 'biggestWin' | 'biggestLoss' | 'maxDrawdown' | 'winRate' | 'trades'

export function Leaderboard() {
  const { pods, traders } = useFund()
  const [sort, setSort] = useState<SortKey>('livePnl')

  const podOf = useMemo(() => new Map(pods.map((p) => [p.id, p])), [pods])

  const ranked = useMemo(() => {
    const arr = [...traders]
    arr.sort((a, b) => {
      const av = a[sort]
      const bv = b[sort]
      // for drawdown/biggestLoss less-negative is "better", so sort ascending-by-magnitude differently
      if (sort === 'maxDrawdown' || sort === 'biggestLoss') return bv - av
      return bv - av
    })
    return arr
  }, [traders, sort])

  if (traders.length === 0) {
    return (
      <div>
        <h1 className="font-serif text-4xl">Leaderboard</h1>
        <NoData title="No traders yet" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <header className="border-b border-rule pb-3">
        <h1 className="font-serif text-4xl">Leaderboard</h1>
        <p className="mt-1 text-xs text-faint">
          Every trader across all pods, ranked by live P&amp;L. Metrics reflect each trader's attributed trades and
          open positions, marked to live market data.
        </p>
      </header>

      <div className="overflow-x-auto border border-rule">
        <table className="dtable">
          <thead>
            <tr>
              <th>#</th>
              <th>Trader</th>
              <th>Pod</th>
              <SortTh k="livePnl" sort={sort} setSort={setSort}>Live P&L</SortTh>
              <SortTh k="realizedPnl" sort={sort} setSort={setSort}>Realized</SortTh>
              <SortTh k="biggestWin" sort={sort} setSort={setSort}>Highest Gain</SortTh>
              <SortTh k="biggestLoss" sort={sort} setSort={setSort}>Biggest Loss</SortTh>
              <SortTh k="maxDrawdown" sort={sort} setSort={setSort}>Max Drawdown</SortTh>
              <SortTh k="winRate" sort={sort} setSort={setSort}>Win Rate</SortTh>
              <SortTh k="trades" sort={sort} setSort={setSort}>Trades</SortTh>
            </tr>
          </thead>
          <tbody>
            {ranked.map((t, i) => {
              const pod = podOf.get(t.podId)
              return (
                <tr key={t.id}>
                  <td className="text-faint">{i + 1}</td>
                  <td>
                    <span className="flex items-center gap-2">
                      <PodGlyph tint={t.tint} label={t.name} size={20} />
                      <span className="font-semibold">{t.name}</span>
                      {t.role === 'pm' && <span className="chip py-0">PM</span>}
                    </span>
                  </td>
                  <td>
                    {pod && (
                      <Link to={`/pods/${pod.code}`} className="underline underline-offset-2">
                        {pod.code}: {pod.name}
                      </Link>
                    )}
                  </td>
                  <td className="text-right"><Money value={t.livePnl} signed /></td>
                  <td className="text-right"><Money value={t.realizedPnl} signed /></td>
                  <td className="text-right pos">{t.biggestWin > 0 ? `+${formatCurrency(t.biggestWin)}` : '—'}</td>
                  <td className="text-right neg">{t.biggestLoss < 0 ? formatCurrency(t.biggestLoss) : '—'}</td>
                  <td className="text-right neg">{(t.maxDrawdown * 100).toFixed(1)}%</td>
                  <td className="text-right num">{(t.winRate * 100).toFixed(0)}%</td>
                  <td className="text-right num">{t.trades}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* pod standings cards (Alpha Arena bottom strip) */}
      <div>
        <h2 className="label-strong mb-2">Pod Standings</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[...pods]
            .sort((a, b) => b.totalReturn - a.totalReturn)
            .map((p, i) => (
              <Link key={p.id} to={`/pods/${p.code}`} className="card px-4 py-4 hover:bg-paper">
                <div className="flex items-center justify-between">
                  <span className="label">Rank {i + 1}</span>
                  <Pct value={p.totalReturn} />
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <PodGlyph tint={p.tint} label={p.name} size={32} />
                  <div>
                    <div className="text-sm font-semibold">{p.code}: {p.name}</div>
                    <div className="text-2xs text-faint">{p.strategy}</div>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-2xs">
                  <KV k="Account" v={formatCurrency(p.accountValue)} />
                  <KV k="Net P&L" v={<Money value={p.totalPnl} signed />} />
                  <KV k="Sharpe" v={p.sharpe.toFixed(2)} />
                  <KV k="Max DD" v={<span className="neg">{(p.maxDrawdown * 100).toFixed(1)}%</span>} />
                </div>
              </Link>
            ))}
        </div>
      </div>

      <p className="text-2xs text-faint">
        Note: realized metrics reflect completed trades; live P&amp;L includes unrealized marks on open positions.
      </p>
    </div>
  )
}

function SortTh({
  k,
  sort,
  setSort,
  children,
}: {
  k: SortKey
  sort: SortKey
  setSort: (k: SortKey) => void
  children: React.ReactNode
}) {
  return (
    <th className="text-right">
      <button
        onClick={() => setSort(k)}
        className={cn('uppercase tracking-[0.1em] hover:text-ink', sort === k ? 'text-ink underline underline-offset-2' : '')}
      >
        {children}
      </button>
    </th>
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
