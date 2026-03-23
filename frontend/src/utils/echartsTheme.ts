import type { EChartsOption } from 'echarts'

export const tooltipStyle = (trigger: 'axis' | 'item' = 'axis'): EChartsOption['tooltip'] => ({
  trigger,
  backgroundColor: 'rgba(255, 255, 255, 0.95)',
  borderColor: '#e8e8ed',
  borderWidth: 1,
  textStyle: { color: '#1d1d1f', fontSize: 12 },
  padding: 12,
  borderRadius: 12,
  shadowBlur: 20,
  shadowColor: 'rgba(0, 0, 0, 0.1)'
})

export const gridStyle = (extra?: Partial<NonNullable<EChartsOption['grid']>>): EChartsOption['grid'] => ({
  left: '3%',
  right: '4%',
  bottom: '3%',
  containLabel: true,
  ...extra
})

export const categoryAxisStyle = (): Partial<NonNullable<EChartsOption['xAxis']>> => ({
  axisLine: { lineStyle: { color: '#e8e8ed', width: 1 } },
  axisLabel: { color: '#86868b', fontSize: 11 },
  axisTick: { show: false }
})

export const valueAxisStyle = (): Partial<NonNullable<EChartsOption['yAxis']>> => ({
  axisLine: { show: false },
  axisLabel: { color: '#86868b', fontSize: 11 },
  splitLine: { lineStyle: { color: '#f5f5f7', type: 'dashed' } }
})

export const legendStyle = (extra?: Record<string, any>): EChartsOption['legend'] => ({
  textStyle: { color: '#86868b', fontSize: 12 },
  ...extra
})
