<template>
  <div ref="chartRef" class="w-full" :style="{ height }"></div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import { useECharts } from '@/composables/useECharts'

const props = defineProps<{ option: EChartsOption; height?: string }>()

const chartRef = ref<HTMLElement>()
const { setOption } = useECharts(chartRef)

watch(() => props.option, (opt) => { if (opt) setOption(opt) }, { immediate: true, deep: true })
</script>
