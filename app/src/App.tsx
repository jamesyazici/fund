import { HashRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Activity } from 'lucide-react'
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
            ? 'text-zinc-900 dark:text-white'
            : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-500 dark:hover:text-zinc-300',
        )
      }
    >
      {label}
    </NavLink>
  )
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.10),transparent_30rem),radial-gradient(circle_at_top_right,rgba(16,185,129,0.10),transparent_26rem),#f8fafc] text-zinc-900 dark:bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.18),transparent_30rem),radial-gradient(circle_at_top_right,rgba(16,185,129,0.12),transparent_26rem),#05070d] dark:text-zinc-100">
      <header className="sticky top-0 z-50 border-b border-zinc-200/80 bg-white/75 backdrop-blur-xl dark:border-white/10 dark:bg-zinc-950/70">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-zinc-900 dark:text-white tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 text-white dark:bg-white dark:text-zinc-950">
              <Activity className="h-4 w-4" />
            </span>
            Fund Portal
          </NavLink>
          <nav className="flex items-center gap-4 sm:gap-6">
            <NavItem to="/" label="Overview" />
            <NavItem to="/trades" label="Trades" />
            <NavItem to="/about" label="Methodology" />
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">{children}</main>
      <footer className="border-t border-zinc-200/80 dark:border-white/10 mt-16 py-6 text-center text-xs text-zinc-500 dark:text-zinc-600">
        Public, read-only view · Data sourced from Supabase · Updated in real time
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
