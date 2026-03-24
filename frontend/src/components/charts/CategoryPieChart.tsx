import type { EChartsOption } from 'echarts'
import type { ECElementEvent } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Card, Empty } from 'antd'
import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import type { CategoryBreakdownResponse } from '../../types/dashboard'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

interface Props {
  data?: CategoryBreakdownResponse
  loading: boolean
  onSelect: (category: string) => void
}

export function CategoryPieChart({ data, loading, onSelect }: Props) {
  const items = data?.items ?? []

  const option = useMemo<EChartsOption>(
    () => ({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          data: items.map((item) => ({ name: item.category, value: item.amount })),
        },
      ],
    }),
    [items],
  )

  if (!loading && items.length === 0) {
    return (
      <Card title="分类占比">
        <div className="chart-empty-state">
          <Empty description="暂无数据" />
        </div>
      </Card>
    )
  }

  return (
    <Card title="分类占比" loading={loading}>
      <ReactEChartsCore
        echarts={echarts}
        style={{ height: 320 }}
        option={option}
        onEvents={{
          click: (params: ECElementEvent) => {
            if (params.name) onSelect(String(params.name))
          },
        }}
      />
    </Card>
  )
}
