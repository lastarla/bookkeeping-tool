import { useState } from 'react'
import { Card, Empty, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { TablePaginationConfig } from 'antd/es/table'
import type { Transaction } from '../../types/transaction'

const DIRECTION_LABELS: Record<string, { label: string; color: string }> = {
  income: { label: '收入', color: 'green' },
  expense: { label: '支出', color: 'red' },
  neutral: { label: '不计收支', color: 'default' },
}

const PLATFORM_LABELS: Record<string, string> = {
  wx: '微信',
  alipay: '支付宝',
}

const MAX_VISIBLE_ROWS = 10
const TABLE_ROW_HEIGHT = 54

const columns: ColumnsType<Transaction> = [
  { title: '日期', dataIndex: 'trade_date', key: 'trade_date' },
  {
    title: '收支类型',
    dataIndex: 'direction',
    key: 'direction',
    render: (direction: string) => {
      const mapped = DIRECTION_LABELS[direction]
      return <Tag color={mapped?.color}>{mapped?.label ?? direction ?? '-'}</Tag>
    },
  },
  { title: '分类', dataIndex: 'category', key: 'category', render: (value: string | null) => value || '-' },
  { title: '类型', dataIndex: 'transaction_type', key: 'transaction_type', render: (value: string | null) => value || '-' },
  { title: '金额', dataIndex: 'amount', key: 'amount' },
  {
    title: '平台',
    dataIndex: 'platform',
    key: 'platform',
    render: (platform: string | null) => (platform ? (PLATFORM_LABELS[platform] ?? platform) : '-'),
  },
]

interface Props {
  rows: Transaction[]
  loading: boolean
}

export function TransactionTable({ rows, loading }: Props) {
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
  })

  const pageSize = pagination.pageSize ?? 10
  const visibleRows = Math.min(pageSize, MAX_VISIBLE_ROWS)
  const scrollY = visibleRows * TABLE_ROW_HEIGHT

  return (
    <Card title="交易明细">
      <Table<Transaction>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={rows}
        locale={{ emptyText: <Empty description="暂无数据" /> }}
        pagination={pagination}
        onChange={(nextPagination) => {
          setPagination((prev) => ({
            ...prev,
            current: nextPagination.current ?? prev.current,
            pageSize: nextPagination.pageSize ?? prev.pageSize,
          }))
        }}
        scroll={{ x: 800, y: scrollY }}
      />
    </Card>
  )
}
