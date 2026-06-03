import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

export type Theme = 'light' | 'dark' | 'system'
type Resolved = 'light' | 'dark'

interface ThemeContextValue {
  theme: Theme
  resolvedTheme: Resolved
  setTheme: (t: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_KEY = 'theme'

function getSystem(): Resolved {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyClass(resolved: Resolved) {
  document.documentElement.classList.toggle('dark', resolved === 'dark')
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'system'
    return (localStorage.getItem(STORAGE_KEY) as Theme) || 'system'
  })

  const [resolvedTheme, setResolvedTheme] = useState<Resolved>(() => {
    if (typeof window === 'undefined') return 'dark'
    const t = (localStorage.getItem(STORAGE_KEY) as Theme) || 'system'
    return t === 'system' ? getSystem() : t
  })

  // Apply theme whenever the preference changes.
  useEffect(() => {
    const resolved = theme === 'system' ? getSystem() : theme
    setResolvedTheme(resolved)
    applyClass(resolved)
  }, [theme])

  // Live-sync with the OS when following the system setting.
  useEffect(() => {
    if (theme !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      const resolved = getSystem()
      setResolvedTheme(resolved)
      applyClass(resolved)
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  const setTheme = (t: Theme) => {
    localStorage.setItem(STORAGE_KEY, t)
    setThemeState(t)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
