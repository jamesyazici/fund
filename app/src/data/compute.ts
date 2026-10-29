import type { NavPoint } from './types'

export const round = (n: number, d = 2) => {
  const f = 10 ** d
  return Math.round(n * f) / f
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
