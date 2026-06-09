import type { NavPoint } from './types'

export const round = (n: number, d = 2) => {
  const f = 10 ** d
  return Math.round(n * f) / f
}

// Annualized Sharpe from a NAV series (assumes ~daily spacing; 0 if too short).
export function sharpeOf(nav: NavPoint[]): number {
  if (nav.length < 3) return 0
  const rets: number[] = []
  for (let i = 1; i < nav.length; i++) {
    const prev = nav[i - 1].value
    if (prev) rets.push(nav[i].value / prev - 1)
  }
  if (rets.length < 2) return 0
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length - 1)
  const sd = Math.sqrt(variance)
  if (sd === 0) return 0
  return round((mean / sd) * Math.sqrt(252), 3)
}

export function maxDrawdownOf(nav: NavPoint[]): number {
  if (nav.length < 2) return 0
  let peak = -Infinity
  let mdd = 0
  for (const p of nav) {
    if (p.value > peak) peak = p.value
    if (peak > 0) {
      const dd = p.value / peak - 1
      if (dd < mdd) mdd = dd
    }
  }
  return round(mdd, 4)
}
