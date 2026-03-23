import { onBeforeUnmount, type Ref, type ShallowRef, shallowRef } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

export function useECharts(chartRef: Ref<HTMLElement | undefined>) {
  const chart: ShallowRef<echarts.ECharts | null> = shallowRef(null)

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
