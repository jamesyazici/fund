import { HashRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Overview } from '@/pages/Overview'
import { PodDetail } from '@/pages/PodDetail'
import { Trades } from '@/pages/Trades'
import { About } from '@/pages/About'
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
    <div className="min-h-screen bg-[#050706] text-zinc-100">
      <main className="mx-auto max-w-[1440px] px-3 py-3 sm:px-5 sm:py-5">{children}</main>
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
