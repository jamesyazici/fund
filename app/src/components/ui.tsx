import { cn } from '@/lib/cn'
import type { Tint } from '@/data/types'
import { formatCurrency, formatPct } from '@/lib/formatters'
import { backendUrl } from '@/lib/backend'

const TINT_BG: Record<Tint, string> = {
  p1: 'bg-p1',
  p2: 'bg-p2',
  p3: 'bg-p3',
  p4: 'bg-p4',
  p5: 'bg-p5',
  p6: 'bg-p6',
}

// pastel square glyph used for pods & traders (Alpha Arena model avatars)
export function PodGlyph({ tint, label, size = 28 }: { tint: Tint; label: string; size?: number }) {
  return (
    <span
      className={cn('inline-grid place-items-center border border-rule font-semibold text-ink', TINT_BG[tint])}
      style={{ width: size, height: size, fontSize: size * 0.42 }}
      aria-hidden
    >
      {label.slice(0, 1).toUpperCase()}
    </span>
  )
}

// colored signed money
export function Money({
  value,
  className,
  decimals = 2,
  signed = false,
}: {
  value: number | null | undefined
  className?: string
  decimals?: number
  signed?: boolean
}) {
  const v = value ?? 0
  const color = !signed ? '' : v > 0 ? 'pos' : v < 0 ? 'neg' : ''
  const prefix = signed && v > 0 ? '+' : ''
  return <span className={cn('num', color, className)}>{prefix}{formatCurrency(v, decimals)}</span>
}

// colored signed percent (input is a fraction)
export function Pct({ value, className }: { value: number | null | undefined; className?: string }) {
  const v = value ?? 0
  const color = v > 0 ? 'pos' : v < 0 ? 'neg' : ''
  return <span className={cn('num', color, className)}>{formatPct(v)}</span>
}

export function Stat({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      <span className="label">{label}</span>
      <span className="text-sm num">{children}</span>
    </div>
  )
}

export function SectionTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn('font-serif text-3xl tracking-tight', className)}>{children}</h2>
}

export function EmptyState({ title, hint }: { title: string; hint?: React.ReactNode }) {
  return (
    <div className="card-soft mx-auto my-10 max-w-xl px-6 py-12 text-center">
      <div className="font-serif text-2xl">{title}</div>
      {hint && <p className="mt-3 text-xs leading-relaxed text-faint">{hint}</p>}
    </div>
  )
}

const HOW_TO = (
  <>
    No live data yet. Create a pod and trader accounts in the{' '}
    <a href={backendUrl('/portal')} className="underline underline-offset-4">admin portal</a>, attach Alpaca paper
    credentials, then place trades with the <code className="bg-paper px-1">rqfc</code> package — everything here
    updates automatically, marked to live market data.
  </>
)

export function NoData({ title }: { title: string }) {
  return <EmptyState title={title} hint={HOW_TO} />
}

export function SideBadge({ side }: { side: 'long' | 'short' | 'buy' | 'sell' }) {
  const isUp = side === 'long' || side === 'buy'
  return (
    <span className={cn('text-2xs font-semibold uppercase tracking-[0.1em]', isUp ? 'text-long' : 'text-short')}>
      {side}
    </span>
  )
}
