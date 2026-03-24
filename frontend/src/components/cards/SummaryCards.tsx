import { Card, Col, Row, Statistic } from 'antd'
import type { OverviewResponse } from '../../types/dashboard'

interface Props {
  overview?: OverviewResponse
  loading: boolean
}

export function SummaryCards({ overview, loading }: Props) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={12} xl={6}>
        <Card loading={loading}><Statistic title="总收入" value={overview?.total_income ?? 0} precision={2} /></Card>
      </Col>
      <Col xs={24} md={12} xl={6}>
        <Card loading={loading}><Statistic title="总支出" value={overview?.total_expense ?? 0} precision={2} /></Card>
      </Col>
      <Col xs={24} md={12} xl={6}>
        <Card loading={loading}><Statistic title="净额" value={overview?.net_amount ?? 0} precision={2} /></Card>
      </Col>
      <Col xs={24} md={12} xl={6}>
        <Card loading={loading}><Statistic title="交易笔数" value={overview?.transaction_count ?? 0} /></Card>
      </Col>
    </Row>
  )
}
