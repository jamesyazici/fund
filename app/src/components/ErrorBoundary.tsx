import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
  info: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to console for debugging in addition to the on-screen panel.
    console.error('Render error caught by ErrorBoundary:', error, info)
    this.setState({ info })
  }

  render() {
    const { error, info } = this.state
    if (!error) return this.props.children

    return (
      <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 p-6 flex items-center justify-center">
        <div className="max-w-2xl w-full rounded-2xl border border-red-500/30 bg-red-500/5 p-6">
          <h1 className="text-lg font-bold text-red-600 dark:text-red-400 mb-2">Something went wrong</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
            The page hit a runtime error while rendering. Details below:
          </p>
          <pre className="text-xs bg-zinc-100 dark:bg-black/40 rounded-lg p-4 overflow-auto text-red-600 dark:text-red-300 whitespace-pre-wrap">
            {error.name}: {error.message}
            {info?.componentStack ? `\n\nComponent stack:${info.componentStack}` : ''}
            {error.stack ? `\n\nStack:\n${error.stack}` : ''}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 rounded-lg bg-zinc-200 hover:bg-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-sm"
          >
            Reload
          </button>
        </div>
      </div>
    )
  }
}
