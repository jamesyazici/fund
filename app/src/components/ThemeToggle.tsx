import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme, type Theme } from '@/lib/theme'
import { cn } from '@/lib/cn'

const OPTIONS: { value: Theme; icon: typeof Sun; label: string }[] = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'system', icon: Monitor, label: 'System' },
  { value: 'dark', icon: Moon, label: 'Dark' },
]

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex items-center gap-0.5 rounded-full border border-zinc-200 dark:border-white/10 p-0.5">
      {OPTIONS.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          aria-label={`${label} theme`}
          aria-pressed={theme === value}
          title={`${label} theme`}
          className={cn(
            'flex items-center justify-center w-7 h-7 rounded-full transition-colors',
            theme === value
              ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900'
              : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white',
          )}
        >
          <Icon className="w-3.5 h-3.5" strokeWidth={2.25} />
        </button>
      ))}
    </div>
  )
}
