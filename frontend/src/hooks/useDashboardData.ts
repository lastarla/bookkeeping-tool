import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCategoryBreakdown, getDefaultPeriod, getOverview, getOwners, getPlatforms, getTrend } from '../api/dashboard'
import type { DashboardFiltersState, DirectionFilter, DashboardView } from '../types/dashboard'

export function useDashboardData() {
  const defaultPeriodQuery = useQuery({
    queryKey: ['default-period'],
    queryFn: getDefaultPeriod,
  })

  const ownersQuery = useQuery({
    queryKey: ['owners'],
    queryFn: getOwners,
  })

  const platformsQuery = useQuery({
    queryKey: ['platforms'],
    queryFn: getPlatforms,
  })

  const [filters, setFilters] = useState<DashboardFiltersState>({
    view: 'monthly',
    month: '',
    year: '',
    direction: 'all',
    owner: 'all',
    platform: 'all',
    includeNeutral: true,
  })

  useEffect(() => {
    if (!defaultPeriodQuery.data) {
      return
    }
    setFilters((prev) => ({
      ...prev,
      month: prev.month || defaultPeriodQuery.data.month,
      year: prev.year || defaultPeriodQuery.data.year,
    }))
  }, [defaultPeriodQuery.data])

  const setView = (view: DashboardView) => {
    setFilters((prev) => ({
      ...prev,
      view,
      month: defaultPeriodQuery.data?.month ?? prev.month,
      year: defaultPeriodQuery.data?.year ?? prev.year,
    }))
  }

  const resetFilters = () => {
    setFilters({
      view: 'monthly',
      month: defaultPeriodQuery.data?.month ?? '',
      year: defaultPeriodQuery.data?.year ?? '',
      direction: 'all',
      owner: 'all',
      platform: 'all',
      includeNeutral: true,
    })
  }

  const enabled = Boolean(filters.month && filters.year)

  const overviewQuery = useQuery({
    queryKey: ['overview', filters],
    queryFn: () => getOverview(filters),
    enabled,
  })

  const categoryDirection: DirectionFilter = filters.direction === 'all' ? 'expense' : filters.direction
  const categoryQuery = useQuery({
    queryKey: ['category', filters, categoryDirection],
    queryFn: () => getCategoryBreakdown({ ...filters, direction: categoryDirection }),
    enabled,
  })

  const trendQuery = useQuery({
    queryKey: ['trend', filters],
    queryFn: () => getTrend(filters),
    enabled,
  })

  return {
    filters,
    setFilters,
    setView,
    resetFilters,
    overviewQuery,
    categoryQuery,
    trendQuery,
    owners: ownersQuery.data ?? [],
    ownersLoading: ownersQuery.isLoading,
    platforms: platformsQuery.data ?? [],
    platformsLoading: platformsQuery.isLoading,
    refetchAll: () => Promise.all([overviewQuery.refetch(), categoryQuery.refetch(), trendQuery.refetch(), ownersQuery.refetch(), platformsQuery.refetch()]),
  }
}
