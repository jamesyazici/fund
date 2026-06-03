import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/db'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url || !key) {
  console.warn('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY — using mock data.')
}

export const supabase = createClient<Database>(
  url ?? 'https://placeholder.supabase.co',
  key ?? 'placeholder',
)
