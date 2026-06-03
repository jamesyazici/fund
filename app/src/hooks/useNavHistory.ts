import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { NavHistorySchema } from '@/types/db'
import { z } from 'zod'

export function useNavHistory(podId: string, days = 365) {
  return useQuery({
    queryKey: ['nav_history', podId, days],
    queryFn: async () => {
      const since = new Date()
      since.setDate(since.getDate() - days)
      const { data, error } = await supabase
        .from('nav_history')
        .select('*')
        .eq('pod_id', podId)
        .gte('date', since.toISOString().slice(0, 10))
        .order('date')
      if (error) throw error
      return z.array(NavHistorySchema).parse(data)
    },
    enabled: !!podId,
    staleTime: 60_000,
  })
}
