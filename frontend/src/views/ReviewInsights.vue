<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h2 class="text-2xl font-bold tracking-tight text-surface-900 dark:text-surface-0">问题分析</h2>
        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">按问题类型、责任人、时间频次查看结构化审查结果</p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <SelectButton
          v-model="days"
          :options="dayOptions"
          option-label="label"
          option-value="value"
          size="small"
        />
        <Select
          v-model="selectedOwner"
          :options="ownerOptions"
          option-label="label"
          option-value="value"
          class="w-[220px]"
          placeholder="按责任人筛选（可选）"
        />
        <Button label="刷新" size="small" :loading="loading" @click="loadStats" />
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card>
        <template #content>
          <div class="text-xs uppercase tracking-wide text-surface-500">问题总数</div>
          <div class="mt-2 text-4xl font-bold text-surface-900 dark:text-surface-0">{{ stats.total_findings }}</div>
        </template>
      </Card>

      <Card>
        <template #content>
          <div class="text-xs uppercase tracking-wide text-surface-500">TOP 问题类型</div>
          <div class="mt-2 text-xl font-semibold text-surface-900 dark:text-surface-0">{{ topCategory.name }}</div>
          <div class="mt-1 text-sm text-surface-500">{{ topCategory.value }} 次</div>
        </template>
      </Card>

      <Card>
        <template #content>
          <div class="text-xs uppercase tracking-wide text-surface-500">TOP 责任人</div>
          <div class="mt-2 text-xl font-semibold text-surface-900 dark:text-surface-0">{{ topOwner.name }}</div>
          <div class="mt-1 text-sm text-surface-500">{{ topOwner.value }} 次</div>
        </template>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">问题频次趋势</div>
        </template>
        <template #content>
          <LineChart :option="trendOption" height="320px" />
        </template>
      </Card>

      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">问题类型分布</div>
        </template>
        <template #content>
          <PieChart :option="categoryOption" height="320px" />
        </template>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">责任人分布</div>
        </template>
        <template #content>
          <BarChart :option="ownerOption" height="320px" />
        </template>
      </Card>

      <Card>
        <template #title>
          <div class="text-sm font-semibold text-surface-800 dark:text-surface-100">严重度分布</div>
        </template>
        <template #content>
          <div class="space-y-3">
            <div
              v-for="item in stats.by_severity"
              :key="item.name"
              class="flex items-center justify-between rounded-lg border border-surface-200/70 bg-surface-50 px-3 py-2 dark:border-surface-700/70 dark:bg-surface-900"
            >
              <Tag :severity="severityTag(item.name)">{{ severityLabel(item.name) }}</Tag>
              <span class="font-semibold text-surface-900 dark:text-surface-0">{{ item.value }}</span>
            </div>
            <div v-if="stats.by_severity.length === 0" class="py-6 text-center text-sm text-surface-500">
              暂无严重度数据
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import { getReviewFindingsStats } from '@/api/index'
import { toast } from '@/utils/toast'
import { categoryAxisStyle, gridStyle, legendStyle, tooltipStyle, valueAxisStyle } from '@/utils/echartsTheme'
import LineChart from '@/components/charts/LineChart.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'
import Select from 'primevue/select'

interface StatsBucket {
  name: string
  value: number
}

interface TrendBucket {
  date: string
  value: number
}

interface ReviewFindingStats {
  total_findings: number
  by_category: StatsBucket[]
  by_severity: StatsBucket[]
  by_owner: StatsBucket[]
  daily_trend: TrendBucket[]
}

const loading = ref(false)
const selectedOwner = ref('')
const ownerDirectory = ref<string[]>([])
const days = ref(30)
const dayOptions = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 },
]

const ownerOptions = computed(() => {
  const options = ownerDirectory.value.map((name) => ({ label: name, value: name }))
  return [{ label: '全部责任人', value: '' }, ...options]
})

const stats = ref<ReviewFindingStats>({
  total_findings: 0,
  by_category: [],
  by_severity: [],
  by_owner: [],
  daily_trend: [],
})

const topCategory = computed(() => stats.value.by_category[0] || { name: '-', value: 0 })
const topOwner = computed(() => stats.value.by_owner[0] || { name: '-', value: 0 })

const trendOption = computed<EChartsOption>(() => ({
  tooltip: tooltipStyle('axis'),
  grid: gridStyle({ left: '4%', right: '4%', top: '10%', bottom: '6%' }),
  xAxis: {
    type: 'category',
    data: stats.value.daily_trend.map((item) => item.date.slice(5)),
    ...categoryAxisStyle(),
  },
  yAxis: {
    type: 'value',
    ...valueAxisStyle(),
  },
  series: [
    {
      type: 'line',
      data: stats.value.daily_trend.map((item) => item.value),
      smooth: true,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { width: 3, color: '#2563eb' },
      itemStyle: { color: '#2563eb' },
      areaStyle: {
        color: 'rgba(37, 99, 235, 0.15)',
      },
    },
  ],
}))

const categoryOption = computed<EChartsOption>(() => ({
  tooltip: tooltipStyle('item'),
  legend: legendStyle({ bottom: 0 }),
  series: [
    {
      type: 'pie',
      radius: ['40%', '72%'],
      avoidLabelOverlap: true,
      data: stats.value.by_category.map((item) => ({ name: item.name, value: item.value })),
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        formatter: '{b}: {d}%'
      },
    },
  ],
}))

const ownerOption = computed<EChartsOption>(() => ({
  tooltip: tooltipStyle('axis'),
  grid: gridStyle({ left: '4%', right: '4%', top: '10%', bottom: '8%' }),
  xAxis: {
    type: 'category',
    data: stats.value.by_owner.slice(0, 10).map((item) => item.name),
    ...categoryAxisStyle(),
    axisLabel: {
      rotate: 25,
      color: '#86868b',
      fontSize: 11,
    },
  },
  yAxis: {
    type: 'value',
    ...valueAxisStyle(),
  },
  series: [
    {
      type: 'bar',
      data: stats.value.by_owner.slice(0, 10).map((item) => item.value),
      barWidth: '45%',
      itemStyle: {
        color: '#16a34a',
        borderRadius: [8, 8, 0, 0],
      },
    },
  ],
}))

const loadStats = async () => {
  loading.value = true
  try {
    const resp = await getReviewFindingsStats({
      days: days.value,
      owner: selectedOwner.value || undefined,
    })

    stats.value = {
      total_findings: Number(resp?.total_findings || 0),
      by_category: Array.isArray(resp?.by_category) ? resp.by_category : [],
      by_severity: Array.isArray(resp?.by_severity) ? resp.by_severity : [],
      by_owner: Array.isArray(resp?.by_owner) ? resp.by_owner : [],
      daily_trend: Array.isArray(resp?.daily_trend) ? resp.daily_trend : [],
    }

    const existing = new Set(ownerDirectory.value)
    for (const item of stats.value.by_owner) {
      const name = String(item?.name || '').trim()
      if (!name || name.toLowerCase() === 'unknown') continue
      existing.add(name)
    }
    ownerDirectory.value = [...existing].sort((a, b) => a.localeCompare(b))
  } catch (error) {
    console.error('加载结构化问题统计失败:', error)
    toast.error('加载结构化问题统计失败')
  } finally {
    loading.value = false
  }
}

const severityTag = (severity: string): 'danger' | 'warn' | 'success' | 'info' | 'secondary' => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical' || normalized === 'high') return 'danger'
  if (normalized === 'medium') return 'warn'
  if (normalized === 'low') return 'success'
  return 'secondary'
}

const severityLabel = (severity: string): string => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical') return '阻断'
  if (normalized === 'high') return '严重'
  if (normalized === 'medium') return '中等'
  if (normalized === 'low') return '轻微'
  return severity || '未知'
}

onMounted(() => {
  loadStats()
})

watch(days, () => {
  loadStats()
})

watch(selectedOwner, () => {
  loadStats()
})
</script>
