import { Link } from 'react-router-dom'
import { usePods } from '@/hooks/usePods'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { useMembers } from '@/hooks/useMembers'
import { ConsoleShell } from '@/components/ConsoleShell'
import { ConsoleTradeFeed } from '@/components/ConsoleTradeFeed'
import { formatCurrency } from '@/lib/formatters'

function TraderRoster({ podId }: { podId?: string }) {
  const { data: members } = useMembers(podId)
  return (
    <div className="space-y-1">
      {(members ?? []).slice(0, 4).map((member) => (
        <div key={member.id}>{member.name} / {member.role.toUpperCase()}</div>
      ))}
      {!members?.length && <div>No assigned traders</div>}
    </div>
  )
}

export function Models() {
  const { data: pods, isLoading, error } = usePods()
  const { data: livePods } = useLiveSnapshots()

  if (isLoading) return <div className="min-h-screen border border-black bg-white" />
  if (error || !pods?.length) return <div className="grid min-h-screen place-items-center font-mono">No fund data.</div>

  return (
    <ConsoleShell pods={pods} livePods={livePods} rightSlot={<ConsoleTradeFeed positions={livePods?.flatMap((pod) => pod.positions) ?? []} />}>
      <div className="grid h-full grid-cols-3 overflow-auto bg-white font-mono text-[11px] max-lg:grid-cols-1">
        {pods.map((pod) => {
          const live = livePods?.find((item) => item.id === pod.id)
          return (
            <Link key={pod.id} to={`/pod/${pod.id}`} className="min-h-60 border-b border-r border-black p-4 last:border-r-0">
              <div className="mb-4 flex items-center justify-between">
                <div className="font-black uppercase tracking-[0.12em]">{pod.name}</div>
                <div className="rounded-full border border-black px-2 py-0.5">{live?.live ? 'LIVE' : 'SYNC'}</div>
              </div>
              <div className="mb-4 text-[10px] uppercase text-zinc-500">{pod.asset_class} / {pod.benchmark_symbol}</div>
              <div className="grid grid-cols-2 gap-2 border-y border-black py-3">
                <div>
                  <div className="text-zinc-500">NAV</div>
                  <div className="font-black">{formatCurrency(live?.nav ?? pod.allocated_capital)}</div>
                </div>
                <div>
                  <div className="text-zinc-500">Notional</div>
                  <div className="font-black">{formatCurrency(live?.gross_notional)}</div>
                </div>
              </div>
              <div className="mt-4">
                <div className="mb-1 font-black uppercase">Traders</div>
                <TraderRoster podId={pod.id} />
              </div>
            </Link>
          )
        })}
      </div>
    </ConsoleShell>
  )
}
