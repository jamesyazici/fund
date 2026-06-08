import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { TradeSchema } from '@/types/db'
import { z } from 'zod'

interface TradeFilters {
  podId?: string
  symbol?: string
  limit?: number
}

export function useTrades({ podId, symbol, limit = 100 }: TradeFilters = {}) {
  return useQuery({
    queryKey: ['trades', { podId, symbol, limit }],
    queryFn: async () => {
      let query = supabase
        .from('trades')
        .select('*, traders(display_name), pods(name)')
        .order('executed_at', { ascending: false })
        .limit(limit)
      if (podId) query = query.eq('pod_id', podId)
      if (symbol) query = query.ilike('symbol', `%${symbol}%`)
      const { data, error } = await query
      if (error) throw error
      return z.array(TradeSchema).parse(data)
    },
    staleTime: 5_000,
  })
}
