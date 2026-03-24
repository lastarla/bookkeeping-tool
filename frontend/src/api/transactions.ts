import { apiGet } from './client'
import type { DashboardFiltersState, DrilldownState } from '../types/dashboard'
import type { Transaction } from '../types/transaction'

function getMonthlyEndDate(month: string): string {
  const [year, monthValue] = month.split('-').map(Number)
  const lastDay = new Date(year, monthValue, 0).getDate()
  return `${month}-${String(lastDay).padStart(2, '0')}`
}

export function getDrilldownTransactions(filters: DashboardFiltersState, options: DrilldownState) {
  const params = new URLSearchParams({
    source: options.source,
    view: filters.view,
    limit: '100',
  })

  if (filters.view === 'monthly') {
    params.set('month', filters.month)
    params.set('year', filters.month.slice(0, 4))
  } else {
    params.set('year', filters.year)
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

  if (options.source === 'default') {
    if (filters.view === 'monthly') {
      params.set('start_date', `${filters.month}-01`)
      params.set('end_date', getMonthlyEndDate(filters.month))
    } else {
      params.set('start_date', `${filters.year}-01-01`)
      params.set('end_date', `${filters.year}-12-31`)
    }
    if (filters.direction !== 'all') {
      params.set('direction', filters.direction)
    }
    return apiGet<Transaction[]>(`/api/transactions?${params.toString()}`)
  }

  if (options.category) {
    params.set('category', options.category === '未分类' ? '' : options.category)
  }
  if (options.pointKey) {
    params.set('point_key', options.pointKey)
  }
  if (options.direction) {
    params.set('direction', options.direction)
  }
  return apiGet<Transaction[]>(`/api/dashboard/drilldown?${params.toString()}`)
}
