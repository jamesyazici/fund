import { HashRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Activity, Search } from 'lucide-react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Overview } from '@/pages/Overview'
import { PodDetail } from '@/pages/PodDetail'
import { Trades } from '@/pages/Trades'
import { About } from '@/pages/About'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ThemeToggle } from '@/components/ThemeToggle'
import { ThemeProvider } from '@/lib/theme'
import { cn } from '@/lib/cn'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
})

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        cn(
          'text-sm font-medium transition-colors',
          isActive
            ? 'text-zinc-950 dark:text-white'
            : 'text-zinc-500 hover:text-zinc-950 dark:text-zinc-500 dark:hover:text-zinc-200',
        )
      }
    >
      {label}
    </NavLink>
  )
}

function Layout({ children }: { children: React.ReactNode }) {
  const topics = ['All', 'Equities', 'Crypto', 'Options', 'Fixed Income', 'FX', 'Futures']

  return (
    <div className="min-h-screen bg-[#f4f7f8] text-zinc-950 dark:bg-[#070908] dark:text-zinc-100">
      <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/95 backdrop-blur-xl dark:border-white/10 dark:bg-[#070908]/95">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-zinc-900 dark:text-white tracking-tight">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-950 text-white shadow-sm dark:bg-[#7cffb2] dark:text-[#07100b]">
              <Activity className="h-4 w-4" />
            </span>
            <span className="hidden sm:inline">RQFC Transparency</span>
          </NavLink>
          <div className="hidden min-w-0 flex-1 items-center rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-500 dark:border-white/10 dark:bg-white/[0.04] md:flex">
            <Search className="mr-2 h-4 w-4" />
            Search pods, tickers, trades
          </div>
          <nav className="flex items-center gap-4 sm:gap-5">
            <NavItem to="/" label="Overview" />
            <NavItem to="/trades" label="Trades" />
            <NavItem to="/about" label="Methodology" />
            <ThemeToggle />
          </nav>
        </div>
        <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 pb-3 sm:px-6">
          {topics.map((topic, index) => (
            <span
              key={topic}
              className={cn(
                'shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold',
                index === 0
                  ? 'border-zinc-950 bg-zinc-950 text-white dark:border-[#7cffb2] dark:bg-[#7cffb2] dark:text-[#07100b]'
                  : 'border-zinc-200 bg-white text-zinc-600 dark:border-white/10 dark:bg-white/[0.04] dark:text-zinc-300',
              )}
            >
              {topic}
            </span>
          ))}
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6 sm:py-7">{children}</main>
      <footer className="border-t border-zinc-200/80 dark:border-white/10 mt-16 py-6 text-center text-xs text-zinc-500 dark:text-zinc-600">
        Public, read-only view · Live Alpaca marks with Supabase history fallback
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <HashRouter>
            <Layout>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/pod/:id" element={<PodDetail />} />
                <Route path="/trades" element={<Trades />} />
                <Route path="/about" element={<About />} />
              </Routes>
            </Layout>
          </HashRouter>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
