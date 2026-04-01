<template>
  <div class="space-y-8">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="text-2xs font-medium text-muted-color uppercase tracking-widest">今日审查</div>
          <div class="mb-1.5 text-4xl font-bold tracking-tight text-color">{{ stats.todayReviews }}</div>
          <div :class="['flex items-center gap-1 text-2xs', stats.todayGrowth >= 0 ? 'text-green-600 dark:text-green-300' : 'text-red-500 dark:text-red-300']">
            <TrendingUp v-if="stats.todayGrowth >= 0" class="w-3 h-3" />
            <TrendingDown v-else class="w-3 h-3" />
            <span>较昨日 {{ stats.todayGrowth >= 0 ? '+' : '' }}{{ stats.todayGrowth }}%</span>
          </div>
        </div>
        <BarChart3 class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-primary/25 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="text-2xs font-medium text-muted-color uppercase tracking-widest">本周审查</div>
          <div class="mb-1.5 text-4xl font-bold tracking-tight text-color">{{ stats.weekReviews }}</div>
          <div class="flex items-center gap-1 text-2xs text-muted-color">
            <Calendar class="w-3 h-3" />
            <span>累计审查次数</span>
          </div>
        </div>
        <Activity class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-purple-500/20 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="text-2xs font-medium text-muted-color uppercase tracking-widest">LLM 调用</div>
          <div class="mb-1.5 text-4xl font-bold tracking-tight text-color">{{ stats.llmCalls }}</div>
          <div class="flex items-center gap-1 text-2xs text-muted-color">
            <Zap class="w-3 h-3" />
            <span>今日API调用</span>
          </div>
        </div>
        <MessageSquare class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-orange-500/20 dark:text-surface-600/40" />
      </div>

      <div class="group relative cursor-pointer overflow-hidden rounded-2xl border border-surface-200/60 bg-surface-0 p-6 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg dark:border-surface-700/60 dark:bg-surface-900">
        <div class="relative z-10 flex flex-col">
          <div class="text-2xs font-medium text-muted-color uppercase tracking-widest">成功率</div>
          <div class="mb-1.5 text-4xl font-bold tracking-tight text-color">{{ stats.successRate }}%</div>
          <div class="flex items-center gap-1 text-2xs text-green-600 dark:text-green-300">
            <CheckCircle class="w-3 h-3" />
            <span>审查成功率</span>
          </div>
        </div>
        <Target class="absolute bottom-4 right-4 h-12 w-12 text-surface-300/50 transition-colors duration-300 group-hover:text-green-500/20 dark:text-surface-600/40" />
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card class="lg:col-span-2 dashboard-card">
        <template #title>
          <div class="flex items-center justify-between">
            <h3 class="dashboard-card-title">审查趋势</h3>
            
            <SelectButton
              v-model="chartType"
              :options="chartTypeOptions"
              option-label="label"
              option-value="value"
              size="small"
            />
          </div>
        </template>
        <template #content>
          <LineChart :option="lineChartOption" height="320px" />
        </template>
      </Card>

      <Card class="dashboard-card">
        <template #title>
          <div class="flex items-center justify-between">
            <h3 class="dashboard-card-title">最近活动</h3>
            <span
              v-tooltip.top="compactTooltip(latestReviewId ? '跳转到最新审查详情' : '暂无可跳转的审查记录')"
              class="inline-flex"
            >
              <IconButton
                size="small"
                aria-label="跳转到审查详情"
                :disabled="!latestReviewId"
                @click="goToLatestReviewDetail"
              >
                <ExternalLink class="w-4 h-4" />
              </IconButton>
            </span>
          </div>
        </template>
        <template #content>
          <div class="space-y-4">
            <div v-for="(activity, index) in recentActivities" :key="index" class="flex gap-3 group">
              <div class="flex-shrink-0 mt-1">
                <div :class="['w-2 h-2 rounded-full', activityColorMap[activity.type] || 'bg-surface-400']"></div>
              </div>
              <div class="flex-1 min-w-0 space-y-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-primary-600">!{{ activity.mr_iid }}</span>
                  <span
                    v-if="activity.mr_title"
                    v-tooltip.top="compactTooltip(activity.mr_title)"
                    class="edium text-surface-900 dark:text-surface-100 truncate max-w-[220px]"
                  >
                    {{ activity.mr_title }}
                  </span>
                  <span v-else class="edium text-surface-900 dark:text-surface-100 truncate max-w-[220px]">
                    -
                  </span>
                  <span
                    v-if="canNavigateReview(activity.review_id)"
                    v-tooltip.top="compactTooltip('查看审查详情')"
                    class="inline-flex flex-shrink-0"
                  >
                    <IconButton
                      size="small"
                      aria-label="查看审查详情"
                      @click="goToReviewDetail(activity.review_id)"
                    >
                      <ExternalLink class="w-3.5 h-3.5" />
                    </IconButton>
                  </span>
                  <Tag :severity="activityStatusSeverity[activity.type] || 'secondary'" class="flex-shrink-0">{{ activity.status }}</Tag>
                </div>
                <div class="flex items-center gap-3">
                  <span v-if="activity.score != null" class="inline-flex items-center gap-1 text-2xs text-orange-500 dark:text-orange-300">
                    <Star class="w-3 h-3" />{{ activity.score }}/10
                  </span>
                  <span v-if="activity.model" class="inline-flex items-center gap-1 text-2xs text-purple-500 truncate max-w-[140px]">
                    <Cpu class="w-3 h-3 flex-shrink-0" />{{ activity.model }}
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-x-3 text-2xs text-surface-500">
                  <span v-if="activity.project" class="truncate max-w-[100px]">{{ activity.project }}</span>
                  <span v-if="activity.author" class="inline-flex items-center gap-1">
                    <User class="w-3 h-3" />{{ activity.author }}
                  </span>
                </div>
                <div class="flex items-center gap-x-3 text-2xs text-surface-500">
                  <span
                    v-if="activity.branch"
                    v-tooltip.top="compactTooltip(activity.branch)"
                    class="inline-flex items-center gap-1 truncate max-w-[200px]"
                  >
                    <GitBranch class="w-3 h-3 flex-shrink-0" />{{ activity.branch }}
                  </span>
                  <span class="text-surface-400 dark:text-surface-500">{{ activity.time }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Bottom Charts -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card class="dashboard-card">
        <template #title>
          <h3 class="dashboard-card-title">LLM 模型分布</h3>
        </template>
        <template #content>
          <PieChart :option="pieChartOption" height="288px" />
        </template>
      </Card>

      <Card class="dashboard-card">
        <template #title>
          <h3 class="dashboard-card-title">审查状态分布</h3>
        </template>
        <template #content>
          <BarChart :option="barChartOption" height="288px" />
        </template>
      </Card>
    </div>

    <!-- System Info -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card class="dashboard-card">
        <template #title>
          <div class="flex items-center justify-between">
            <h3 class="dashboard-card-title">系统信息</h3>
            <Tag :severity="systemInfo.serverStatus === 'running' ? 'success' : 'danger'">
              {{ systemInfo.serverStatus === 'running' ? '运行中' : '离线' }}
            </Tag>
          </div>
        </template>
        <template #content>
          <dl class="space-y-3 text-sm">
            <div class="flex items-center justify-between gap-3">
              <dt class="text-surface-500">项目名称</dt>
              <dd class="text-surface-900 dark:text-surface-100 font-medium">{{ systemInfo.projectName }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-surface-500">版本</dt>
              <dd class="text-surface-900 dark:text-surface-100 font-medium">{{ systemInfo.projectVersion }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-surface-500">Python 版本</dt>
              <dd class="text-surface-900 dark:text-surface-100 font-medium">{{ systemInfo.pythonVersion }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-surface-500">框架</dt>
              <dd class="text-surface-900 dark:text-surface-100 font-medium">FastAPI</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-surface-500">运行时间</dt>
              <dd class="text-surface-900 dark:text-surface-100 font-medium">{{ systemInfo.uptime }}</dd>
            </div>
          </dl>
        </template>
      </Card>

      <Card class="dashboard-card">
        <template #title>
          <h3 class="dashboard-card-title">资源使用</h3>
        </template>
        <template #content>
          <div class="space-y-6">
            <div>
              <div class="flex justify-between mb-2">
                <span class="text-surface-600">CPU 使用率</span>
                <span class="edium text-surface-900 dark:text-surface-100">{{ systemInfo.cpu }}%</span>
              </div>
              <ProgressBar :value="cpuProgressPercent" :show-value="false" style="height: 8px" />
            </div>
            <div>
              <div class="flex justify-between mb-2">
                <span class="text-surface-600">内存使用</span>
                <span class="edium text-surface-900 dark:text-surface-100">{{ systemInfo.memoryUsed }} / {{ systemInfo.memoryTotal }}</span>
              </div>
              <ProgressBar :value="memoryProgressPercent" :show-value="false" style="height: 8px" />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { EChartsOption } from 'echarts'
import Tooltip from 'primevue/tooltip'
import {
  TrendingUp, TrendingDown, Calendar, Zap, CheckCircle,
  BarChart3, Activity, MessageSquare, Target,
  User, GitBranch, Star, Cpu, ExternalLink
} from 'lucide-vue-next'
import { tooltipStyle, gridStyle, categoryAxisStyle, valueAxisStyle, legendStyle } from '@/utils/echartsTheme'
import { graphic } from '@/lib/echarts'
import LineChart from '@/components/charts/LineChart.vue'
import PieChart from '@/components/charts/PieChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import IconButton from '@/components/ui/IconButton.vue'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import SelectButton from 'primevue/selectbutton'
import { getDashboardStats, getDashboardCharts, getSystemInfo } from '@/api'

const router = useRouter()
const vTooltip = Tooltip
const compactTooltip = (value: string) => ({
  value,
  class: 'dashboard-compact-tooltip dashboard-activity-tooltip',
  fitContent: true
})

const stats = ref({
  todayReviews: 0, todayGrowth: 0,
  weekReviews: 0, llmCalls: 0, successRate: 0
})

const chartType = ref<'week' | 'month'>('week')
const chartTypeOptions = [
  { label: '近7天', value: 'week' },
  { label: '近30天', value: 'month' }
]
const chartData = ref<any>({
  review_trend: { dates: [], reviews: [], llm_calls: [] },
  llm_distribution: [],
  review_status: [],
  recent_activities: [],
})

const loadStats = async () => {
  try {
    const response = await getDashboardStats()
    if (response) {
      stats.value = {
        todayReviews: response.today_reviews ?? 0,
        todayGrowth: response.today_growth ?? 0,
        weekReviews: response.week_reviews ?? 0,
        llmCalls: response.llm_calls ?? 0,
        successRate: response.success_rate ?? 0,
      }
    }
  } catch (error) {
    console.error('Failed to load dashboard stats:', error)
  }
}

const loadCharts = async () => {
  try {
    const days = chartType.value === 'week' ? 7 : 30
    const response = await getDashboardCharts(days)
    if (response) chartData.value = response
  } catch (error) {
    console.error('Failed to load dashboard charts:', error)
  }
}

const systemInfo = ref({
  uptime: '加载中...', cpu: 0, memory: 0,
  memoryUsed: '0 GB', memoryTotal: '0 GB',
  projectName: 'AI Code Review', projectVersion: '0.0.1',
  pythonVersion: '加载中...', serverStatus: 'running',
})

const normalizeProgressPercent = (value: number): number => {
  if (!Number.isFinite(value)) return 0
  if (value <= 1) return Math.max(0, value)
  return Math.min(1, Math.max(0, value / 100))
}

const cpuProgressPercent = computed(() => Math.round(normalizeProgressPercent(systemInfo.value.cpu) * 100))
const memoryProgressPercent = computed(() => Math.round(normalizeProgressPercent(systemInfo.value.memory) * 100))

let sysTimer: ReturnType<typeof setInterval> | null = null

const fetchSystemInfo = async () => {
  try {
    const response = await getSystemInfo()
    const data = response.data || response
    if (data.status === 'ok') {
      systemInfo.value = {
        uptime: data.uptime, cpu: data.cpu, memory: data.memory,
        memoryUsed: data.memoryUsed, memoryTotal: data.memoryTotal,
        projectName: data.projectName, projectVersion: data.projectVersion,
        pythonVersion: data.pythonVersion, serverStatus: data.serverStatus,
      }
    }
  } catch {
    systemInfo.value.serverStatus = 'offline'
  }
}

watch(chartType, () => loadCharts())
onMounted(() => {
  Promise.all([loadStats(), loadCharts(), fetchSystemInfo()])
  sysTimer = setInterval(fetchSystemInfo, 30000)
})
onBeforeUnmount(() => { if (sysTimer) clearInterval(sysTimer) })

const activityColorMap: Record<string, string> = {
  success: 'bg-green-500', primary: 'bg-primary',
  info: 'bg-surface-400', warning: 'bg-orange-500'
}

const activityStatusSeverity: Record<string, 'success' | 'danger' | 'info' | 'secondary'> = {
  success: 'success', warning: 'danger', primary: 'info', info: 'secondary'
}

const recentActivities = computed(() => chartData.value.recent_activities || [])
const latestReviewId = computed<number | null>(() => {
  const first = recentActivities.value?.[0]
  const value = Number(first?.review_id)
  return Number.isFinite(value) && value > 0 ? value : null
})

const goToLatestReviewDetail = () => {
  if (!latestReviewId.value) {
    return
  }
  router.push(`/reviews/${latestReviewId.value}`)
}

const canNavigateReview = (reviewId: unknown): boolean => {
  const value = Number(reviewId)
  return Number.isFinite(value) && value > 0
}

const goToReviewDetail = (reviewId: unknown) => {
  if (!canNavigateReview(reviewId)) {
    return
  }
  router.push(`/reviews/${Number(reviewId)}`)
}

const lineChartOption = computed<EChartsOption>(() => {
  const trend = chartData.value.review_trend || { dates: [], reviews: [], llm_calls: [] }
  return {
    tooltip: tooltipStyle('axis'),
    legend: legendStyle({ data: ['审查次数', 'LLM调用'], bottom: 0, itemGap: 20 }),
    grid: gridStyle({ bottom: '12%' }),
    xAxis: { type: 'category', data: trend.dates, ...categoryAxisStyle() },
    yAxis: { type: 'value', ...valueAxisStyle() },
    series: [
      {
        name: '审查次数', type: 'line', smooth: true,
        data: trend.reviews,
        lineStyle: { color: '#007aff', width: 3 },
        itemStyle: { color: '#007aff' },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 122, 255, 0.2)' },
            { offset: 1, color: 'rgba(0, 122, 255, 0)' }
          ])
        }
      },
      {
        name: 'LLM调用', type: 'line', smooth: true,
        data: trend.llm_calls,
        lineStyle: { color: '#34c759', width: 3 },
        itemStyle: { color: '#34c759' },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(52, 199, 89, 0.2)' },
            { offset: 1, color: 'rgba(52, 199, 89, 0)' }
          ])
        }
      }
    ]
  }
})

const MODEL_COLORS = ['#007aff', '#34c759', '#af52de', '#ff9500', '#ff3b30', '#5ac8fa', '#ffcc00', '#ff2d55']

const pieChartOption = computed<EChartsOption>(() => {
  const dist = (chartData.value.llm_distribution || []).map((item: any, i: number) => ({
    value: item.value,
    name: item.name,
    itemStyle: { color: MODEL_COLORS[i % MODEL_COLORS.length] }
  }))
  return {
    tooltip: tooltipStyle('item'),
    legend: legendStyle({ orient: 'vertical', right: 10, top: 'center' }),
    series: [{
      type: 'pie', radius: ['45%', '70%'], avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 3 },
      label: { show: false }, labelLine: { show: false },
      data: dist.length > 0 ? dist : [{ value: 1, name: '暂无数据', itemStyle: { color: '#e5e7eb' } }]
    }]
  }
})

const STATUS_COLORS: Record<string, string> = {
  '已完成': '#34c759', '失败': '#ff3b30', '处理中': '#007aff', '待处理': '#ff9500',
}

const barChartOption = computed<EChartsOption>(() => {
  const status = chartData.value.review_status || []
  const xAxisStyle = categoryAxisStyle() as Record<string, any>
  const axisLabelStyle = (xAxisStyle.axisLabel ?? {}) as Record<string, any>
  return {
    tooltip: { ...tooltipStyle('axis'), axisPointer: { type: 'shadow' } } as any,
    grid: gridStyle(),
    xAxis: {
      type: 'category',
      data: status.map((s: any) => s.name),
      ...xAxisStyle,
      axisLabel: { ...axisLabelStyle, interval: 0 }
    },
    yAxis: { type: 'value', ...valueAxisStyle() },
    series: [{
      type: 'bar',
      data: status.map((s: any) => ({
        value: s.value,
        itemStyle: { color: STATUS_COLORS[s.name] || '#af52de' }
      })),
      barWidth: '50%',
      itemStyle: { borderRadius: [8, 8, 0, 0] }
    }]
  }
})
</script>

<style scoped>
.dashboard-card-title {
  color: var(--color-text-1);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.5715;
}

</style>
