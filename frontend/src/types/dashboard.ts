export type DashboardView = 'monthly' | 'yearly'
export type DirectionFilter = 'all' | 'income' | 'expense'

export interface OverviewResponse {
  total_income: number
  total_expense: number
  net_amount: number
  transaction_count: number
}

export interface CategoryBreakdownItem {
  category: string
  amount: number
  count: number
}

export interface CategoryBreakdownResponse {
  direction: 'income' | 'expense'
  items: CategoryBreakdownItem[]
}

export interface TrendResponse {
  labels: string[]
  income: number[]
  expense: number[]
}

export interface DashboardFiltersState {
  view: DashboardView
  month: string
  year: string
  direction: DirectionFilter
  owner: string
  platform: string
  includeNeutral: boolean
}

export interface DrilldownState {
  source: 'category' | 'trend' | 'default'
  category?: string
  pointKey?: string
  direction?: 'income' | 'expense'
}
