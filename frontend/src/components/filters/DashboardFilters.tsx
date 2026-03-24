import { Checkbox, Segmented, DatePicker, Select, Space, Button } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import customParseFormat from 'dayjs/plugin/customParseFormat'
import type { DashboardFiltersState } from '../../types/dashboard'

dayjs.extend(customParseFormat)

const PLATFORM_LABELS: Record<string, string> = {
  wx: '微信',
  alipay: '支付宝',
}

interface Props {
  filters: DashboardFiltersState
  owners: string[]
  ownersLoading: boolean
  platforms: string[]
  platformsLoading: boolean
  onChange: (next: DashboardFiltersState) => void
  onReset: () => void
  onOpenImport: () => void
}

function parseMonth(value: string): Dayjs | null {
  if (!value) {
    return null
  }
  const parsed = dayjs(value, 'YYYY-MM', true)
  return parsed.isValid() ? parsed : null
}

function parseYear(value: string): Dayjs | null {
  if (!value) {
    return null
  }
  const parsed = dayjs(value, 'YYYY', true)
  return parsed.isValid() ? parsed : null
}

export function DashboardFilters({ filters, owners, ownersLoading, platforms, platformsLoading, onChange, onReset, onOpenImport }: Props) {
  return (
    <Space wrap size="middle">
      <Segmented
        value={filters.view}
        options={[
          { label: '月度', value: 'monthly' },
          { label: '年度', value: 'yearly' },
        ]}
        onChange={(value) =>
          onChange({
            ...filters,
            view: value as 'monthly' | 'yearly',
          })
        }
      />
      {filters.view === 'monthly' ? (
        <DatePicker
          picker="month"
          value={parseMonth(filters.month)}
          onChange={(value) => value && onChange({ ...filters, month: value.format('YYYY-MM') })}
        />
      ) : (
        <DatePicker
          picker="year"
          value={parseYear(filters.year)}
          onChange={(value) => value && onChange({ ...filters, year: value.format('YYYY') })}
        />
      )}
      <Select
        style={{ width: 140 }}
        value={filters.direction}
        options={[
          { label: '全部', value: 'all' },
          { label: '收入', value: 'income' },
          { label: '支出', value: 'expense' },
        ]}
        onChange={(value) => onChange({ ...filters, direction: value })}
      />
      <Select
        style={{ width: 160 }}
        value={filters.owner}
        loading={ownersLoading}
        options={[{ label: '全部', value: 'all' }, ...owners.map((owner) => ({ label: owner, value: owner }))]}
        onChange={(value) => onChange({ ...filters, owner: value })}
      />
      <Select
        style={{ width: 160 }}
        value={filters.platform}
        loading={platformsLoading}
        options={[
          { label: '全部', value: 'all' },
          ...platforms.map((platform) => ({ label: PLATFORM_LABELS[platform] ?? platform, value: platform })),
        ]}
        onChange={(value) => onChange({ ...filters, platform: value })}
      />
      <Checkbox checked={filters.includeNeutral} onChange={(event) => onChange({ ...filters, includeNeutral: event.target.checked })}>
        计入不计收支
      </Checkbox>
      <Button onClick={onReset}>重置筛选</Button>
      <Button type="primary" icon={<UploadOutlined />} onClick={onOpenImport}>
        导入账单
      </Button>
    </Space>
  )
}
