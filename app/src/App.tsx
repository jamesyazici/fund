import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { Live } from '@/pages/Live'
import { Leaderboard } from '@/pages/Leaderboard'
import { Pods } from '@/pages/Pods'
import { PodDetail } from '@/pages/PodDetail'
import { About } from '@/pages/About'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <HashRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Live />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route path="/pods" element={<Pods />} />
              <Route path="/pods/:id" element={<PodDetail />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </HashRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
