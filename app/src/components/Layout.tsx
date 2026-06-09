import { Masthead } from './Masthead'
import { useFund } from '@/data/useFund'

export function Layout({ children }: { children: React.ReactNode }) {
  const { isLive } = useFund()
  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <Masthead />
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-5">{children}</main>
      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-5 py-4 text-2xs uppercase tracking-[0.14em] text-faint">
          <span>RQFC — Fund Transparency Portal</span>
          <span className="flex items-center gap-2">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${isLive ? 'bg-gain' : 'bg-faint'}`} />
            {isLive ? 'Live · marked to market' : 'Demo data · marked to market'}
          </span>
          <span>Paper-traded · for transparency & education only</span>
        </div>
      </footer>
    </div>
  )
}
