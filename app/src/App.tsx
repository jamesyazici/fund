import { HashRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Overview } from '@/pages/Overview'
import { PodDetail } from '@/pages/PodDetail'
import { Trades } from '@/pages/Trades'
import { About } from '@/pages/About'
import { Leaderboard } from '@/pages/Leaderboard'
import { Models } from '@/pages/Models'
import { Blog } from '@/pages/Blog'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ThemeProvider } from '@/lib/theme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
})

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white text-black">
      <main>{children}</main>
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
                <Route path="/leaderboard" element={<Leaderboard />} />
                <Route path="/models" element={<Models />} />
                <Route path="/blog" element={<Blog />} />
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
