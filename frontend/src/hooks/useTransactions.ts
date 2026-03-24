import { useQuery } from '@tanstack/react-query'
import { getDrilldownTransactions } from '../api/transactions'
import type { DashboardFiltersState, DrilldownState } from '../types/dashboard'

export function useTransactions(filters: DashboardFiltersState, drilldown?: DrilldownState | null) {
  const effectiveDrilldown: DrilldownState =
    drilldown ??
    ({
      source: 'default',
      direction: filters.direction === 'all' ? undefined : filters.direction,
    } satisfies DrilldownState)

  return useQuery({
    queryKey: ['transactions', filters, effectiveDrilldown],
    queryFn: () => getDrilldownTransactions(filters, effectiveDrilldown),
    enabled: Boolean(filters.month && filters.year),
  })
}
