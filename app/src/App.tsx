import { HashRouter, Routes, Route, NavLink } from 'react-router-dom'
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
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <header className="sticky top-0 z-50 border-b border-zinc-200 bg-zinc-50/80 backdrop-blur-md dark:border-white/5 dark:bg-zinc-950/80">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <NavLink to="/" className="font-bold text-zinc-900 dark:text-white tracking-tight">
            Fund Portal
          </NavLink>
          <nav className="flex items-center gap-6">
            <NavItem to="/" label="Overview" />
            <NavItem to="/trades" label="Trades" />
            <NavItem to="/about" label="Methodology" />
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">{children}</main>
      <footer className="border-t border-zinc-200 dark:border-white/5 mt-16 py-6 text-center text-xs text-zinc-500 dark:text-zinc-600">
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
