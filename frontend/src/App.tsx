import { lazy, Suspense, useEffect, useState } from 'react'
import { Col, Layout, Row, Space, Spin, Typography } from 'antd'
import { DashboardFilters } from './components/filters/DashboardFilters'
import { SummaryCards } from './components/cards/SummaryCards'
import { TransactionTable } from './components/tables/TransactionTable'
import { ImportUploader } from './components/upload/ImportUploader'
import { useDashboardData } from './hooks/useDashboardData'
import { useTransactions } from './hooks/useTransactions'
import type { DrilldownState } from './types/dashboard'

const CategoryPieChart = lazy(() => import('./components/charts/CategoryPieChart').then((module) => ({ default: module.CategoryPieChart })))
const IncomeExpenseBarChart = lazy(() => import('./components/charts/IncomeExpenseBarChart').then((module) => ({ default: module.IncomeExpenseBarChart })))

const { Header, Content } = Layout

export default function App() {
  const {
    filters,
    setFilters,
    setView,
    resetFilters,
    overviewQuery,
    categoryQuery,
    trendQuery,
    owners,
    ownersLoading,
    platforms,
    platformsLoading,
    refetchAll,
  } = useDashboardData()
  const [drilldown, setDrilldown] = useState<DrilldownState | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const transactionsQuery = useTransactions(filters, drilldown)

  useEffect(() => {
    setDrilldown(null)
  }, [filters.view, filters.month, filters.year, filters.direction])

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="app-brand">
          <Typography.Text className="app-brand-kicker">BOOKKEEPING</Typography.Text>
          <Typography.Title level={3} className="app-brand-title">
            收支总览
          </Typography.Title>
        </div>
      </Header>
      <Content className="app-content">
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <DashboardFilters
            filters={filters}
            owners={owners}
            ownersLoading={ownersLoading}
            platforms={platforms}
            platformsLoading={platformsLoading}
            onChange={(next) => {
              if (next.view !== filters.view) {
                setView(next.view)
                return
              }
              setFilters(next)
            }}
            onReset={() => {
              resetFilters()
              setDrilldown(null)
            }}
            onOpenImport={() => setImportOpen(true)}
          />
          <ImportUploader open={importOpen} onClose={() => setImportOpen(false)} onImported={() => void refetchAll()} />
          <SummaryCards overview={overviewQuery.data} loading={overviewQuery.isLoading} />
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <Suspense fallback={<Spin size="large" />}>
                <CategoryPieChart
                  data={categoryQuery.data}
                  loading={categoryQuery.isLoading}
                  onSelect={(category) =>
                    setDrilldown({
                      source: 'category',
                      category,
                      direction: filters.direction === 'income' ? 'income' : 'expense',
                    })
                  }
                />
              </Suspense>
            </Col>
            <Col xs={24} xl={12}>
              <Suspense fallback={<Spin size="large" />}>
                <IncomeExpenseBarChart
                  data={trendQuery.data}
                  loading={trendQuery.isLoading}
                  onSelect={({ pointKey, direction }) => setDrilldown({ source: 'trend', pointKey, direction })}
                />
              </Suspense>
            </Col>
          </Row>
          <TransactionTable rows={transactionsQuery.data ?? []} loading={transactionsQuery.isLoading} />
        </Space>
      </Content>
    </Layout>
  )
}
