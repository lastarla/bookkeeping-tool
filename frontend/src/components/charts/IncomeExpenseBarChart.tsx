import type { EChartsOption } from 'echarts'
import type { ECElementEvent } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Card, Empty } from 'antd'
import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import type { TrendResponse } from '../../types/dashboard'

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

interface Props {
  data?: TrendResponse
  loading: boolean
  onSelect: (payload: { pointKey: string; direction: 'income' | 'expense' }) => void
}

export function IncomeExpenseBarChart({ data, loading, onSelect }: Props) {
  const hasData = Boolean(data && ([...(data.income ?? []), ...(data.expense ?? [])].some((value) => value !== 0)))

  const option = useMemo<EChartsOption>(
    () => ({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 24, right: 24, bottom: 24, containLabel: true },
      xAxis: { type: 'category', data: data?.labels ?? [] },
      yAxis: { type: 'value' },
      series: [
        { name: '收入', type: 'bar', data: data?.income ?? [] },
        { name: '支出', type: 'bar', data: data?.expense ?? [] },
      ],
    }),
    [data],
  )

  if (!loading && !hasData) {
    return (
      <Card title="收支趋势">
        <div className="chart-empty-state">
          <Empty description="暂无数据" />
        </div>
      </Card>
    )
  }

  return (
    <Card title="收支趋势" loading={loading}>
      <ReactEChartsCore
        echarts={echarts}
        style={{ height: 320 }}
        option={option}
        onEvents={{
          click: (params: ECElementEvent) => {
            if (!params.name || !params.seriesName) return
            onSelect({
              pointKey: String(params.name),
              direction: params.seriesName === '收入' ? 'income' : 'expense',
            })
          },
        }}
      />
    </Card>
  )
}
