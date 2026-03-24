import { apiGet } from './client'
import type {
  CategoryBreakdownResponse,
  DashboardFiltersState,
  OverviewResponse,
  TrendResponse,
} from '../types/dashboard'

function periodParams(filters: DashboardFiltersState): URLSearchParams {
  const params = new URLSearchParams({
    view: filters.view,
  })
  if (filters.view === 'monthly') {
    params.set('month', filters.month)
    params.set('year', filters.month.slice(0, 4))
  } else {
    params.set('year', filters.year)
  }
  if (filters.direction) {
    params.set('direction', filters.direction)
  }
  if (filters.owner !== 'all') {
    params.set('owner', filters.owner)
  }
  if (filters.platform !== 'all') {
    params.set('platform', filters.platform)
  }
  if (filters.includeNeutral) {
    params.set('include_neutral', 'true')
  }
  return params
}

export function getDefaultPeriod() {
  return apiGet<{ month: string; year: string }>('/api/meta/default-period')
}

export function getOwners() {
  return apiGet<string[]>('/api/meta/owners')
}

export function getPlatforms() {
  return apiGet<string[]>('/api/meta/platforms')
}

export function getOverview(filters: DashboardFiltersState) {
  return apiGet<OverviewResponse>(`/api/dashboard/overview?${periodParams(filters).toString()}`)
}

export function getCategoryBreakdown(filters: DashboardFiltersState) {
  const params = periodParams(filters)
  params.set('direction', filters.direction === 'all' ? 'expense' : filters.direction)
  return apiGet<CategoryBreakdownResponse>(`/api/dashboard/category-breakdown?${params.toString()}`)
}

export function getTrend(filters: DashboardFiltersState) {
  const params = new URLSearchParams({
    view: filters.view,
    year: filters.view === 'monthly' ? filters.month.slice(0, 4) : filters.year,
  })
  if (filters.owner !== 'all') {
    params.set('owner', filters.owner)
  }
  if (filters.platform !== 'all') {
    params.set('platform', filters.platform)
  }
  if (filters.includeNeutral) {
    params.set('include_neutral', 'true')
  }
  return apiGet<TrendResponse>(`/api/dashboard/trend?${params.toString()}`)
}
