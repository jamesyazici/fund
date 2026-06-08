import { usePods } from '@/hooks/usePods'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { ConsoleShell } from '@/components/ConsoleShell'
import { ConsoleTradeFeed } from '@/components/ConsoleTradeFeed'

export function Blog() {
  const { data: pods, isLoading, error } = usePods()
  const { data: livePods } = useLiveSnapshots()

  if (isLoading) return <div className="min-h-screen border border-black bg-white" />
  if (error || !pods?.length) return <div className="grid min-h-screen place-items-center font-mono">No fund data.</div>

  return (
    <ConsoleShell pods={pods} livePods={livePods} rightSlot={<ConsoleTradeFeed positions={livePods?.flatMap((pod) => pod.positions) ?? []} />}>
      <article className="h-full overflow-auto bg-white p-5 font-mono text-[12px] leading-6">
        <h1 className="mb-4 text-xl font-black uppercase tracking-[0.14em]">RQFC Transparency Readme</h1>
        <pre className="whitespace-pre-wrap">
{`RQFC FUND TRANSPARENCY PORTAL
VERSION: 1.0.0

OVERVIEW:
This portal shows live student fund activity in a public, read-only format.

DATA SOURCES:
1. Alpaca fills are authoritative when available.
2. Recorded trades remain the durable public order log.
3. Live market data marks open positions.
4. Portfolio marks calculate realized, unrealized, and total P&L.

WHAT THE VIEWER CAN SEE:
- Pods and assigned student traders
- Completed trades
- Open positions
- Position size and notional value
- Realized P&L
- Unrealized P&L
- Total P&L
- Live portfolio value movement

NOT INVESTMENT ADVICE:
This is an educational transparency surface for student fund operations.`}
        </pre>
      </article>
    </ConsoleShell>
  )
}
