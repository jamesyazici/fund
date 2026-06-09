import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { Ticker } from './Ticker'

const NAV = [
  { to: '/', label: 'Live', end: true },
  { to: '/leaderboard', label: 'Leaderboard' },
  { to: '/pods', label: 'Pods' },
  { to: '/about', label: 'About' },
]

export function Masthead() {
  return (
    <header className="sticky top-0 z-40 bg-paper">
      <div className="border-b border-rule">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-6 px-5 py-2.5">
          {/* masthead logo */}
          <NavLink to="/" className="flex items-baseline gap-2 leading-none">
            <span className="font-serif text-2xl font-bold tracking-tight">RQFC</span>
            <span className="hidden sm:inline text-2xs uppercase tracking-[0.2em] text-faint">
              Fund&nbsp;Transparency
            </span>
          </NavLink>

          {/* primary nav */}
          <nav className="flex items-center gap-5 sm:gap-7">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) => cn('nav-link', isActive && 'nav-link-active')}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          {/* CTA */}
          <a
            href="https://github.com/"
            target="_blank"
            rel="noreferrer"
            className="hidden md:inline-flex text-2xs uppercase tracking-[0.18em] underline underline-offset-4 hover:no-underline"
          >
            Request fund access ↗
          </a>
        </div>
      </div>

      <Ticker />
    </header>
  )
}
