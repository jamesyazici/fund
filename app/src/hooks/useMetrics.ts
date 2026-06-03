import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { MetricsSchema } from '@/types/db'

export function useMetrics(podId: string) {
  return useQuery({
    queryKey: ['metrics', podId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('metrics')
        .select('*')
        .eq('pod_id', podId)
        .order('as_of_date', { ascending: false })
        .limit(1)
        .single()
      if (error) throw error
      return MetricsSchema.parse(data)
    },
    enabled: !!podId,
    staleTime: 300_000,
  })
}
