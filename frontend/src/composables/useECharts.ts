import { onBeforeUnmount, type Ref, type ShallowRef, shallowRef } from 'vue'
import type { EChartsOption } from 'echarts'
import type { EChartsType } from 'echarts/core'
import { echarts } from '@/lib/echarts'

export function useECharts(chartRef: Ref<HTMLElement | undefined>) {
  const chart: ShallowRef<EChartsType | null> = shallowRef(null)

  const handleResize = () => chart.value?.resize()

  const setOption = (option: EChartsOption) => {
    if (!chartRef.value) return
    if (!chart.value) {
      chart.value = echarts.init(chartRef.value)
      window.addEventListener('resize', handleResize)
    }
    chart.value.setOption(option, true)
  }

  const dispose = () => {
    window.removeEventListener('resize', handleResize)
    chart.value?.dispose()
    chart.value = null
  }

  onBeforeUnmount(dispose)

  return { chart, setOption, dispose }
}
