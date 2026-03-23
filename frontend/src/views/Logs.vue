<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 class="text-xl font-semibold text-surface-800">日志监控</h2>

          <div class="flex flex-wrap items-center gap-3">
            <SelectButton
              v-model="logLevel"
              :options="logLevelOptions"
              option-label="label"
              option-value="value"
              size="small"
            />

            <Button label="刷新" @click="handleRefresh">
              <template #icon><RefreshCw class="h-4 w-4" /></template>
            </Button>

            <Button severity="danger"
              outlined
              label="清空"
              @click="handleClear"
            >
              <template #icon><Trash2 class="h-4 w-4" /></template>
            </Button>
          </div>
        </div>

        <div v-if="loading" class="flex w-full justify-center py-10">
          <div class="h-8 w-8 animate-spin rounded-full border-2 border-surface-300 border-t-primary"></div>
        </div>

        <div v-else class="max-h-[70vh] space-y-4 overflow-y-auto">
          <template v-if="filteredLogs.length > 0">
            <div
              v-for="(log, index) in filteredLogs"
              :key="log.id || index"
              class="overflow-hidden rounded-xl border border-surface-200/50 transition-shadow hover:shadow-sm dark:border-surface-700/60"
            >
              <div class="border-b border-surface-200/50 bg-surface-50 p-4 dark:border-surface-700/50 dark:bg-surface-800/70">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <Tag :severity="getLogSeverity(log.level)">{{ log.level }}</Tag>
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-xs text-surface-500">{{ log.timestamp }}</span>
                      <Tag severity="info">{{ log.event_type || log.module }}</Tag>
                      <Tag v-if="log.project_name" severity="secondary">{{ log.project_name }}</Tag>
                      <Tag v-if="log.merge_request_iid" severity="warn">MR!{{ log.merge_request_iid }}</Tag>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span v-if="log.user_name" class="text-surface-600">{{ log.user_name }}</span>
                    <Button text size="small" @click="toggleDetails(index)">
                      {{ expandedLogs[index] ? '收起' : '展开详情' }}
                    </Button>
                  </div>
                </div>
                <p class="mt-2 edium text-surface-900 dark:text-surface-100">{{ log.message }}</p>
              </div>

              <div v-show="expandedLogs[index]" class="border-t border-surface-200/50 dark:border-surface-700/50">
                <div v-if="log.request_headers || log.request_body" class="border-b border-blue-200 bg-blue-50 p-4 dark:border-blue-500/35 dark:bg-blue-500/10">
                  <h4 class="mb-3 font-semibold text-blue-900 dark:text-blue-200">请求信息</h4>
                  <div v-if="log.request_headers" class="mb-3">
                    <h5 class="mb-2 text-xs font-medium text-blue-800 dark:text-blue-300">Request Headers:</h5>
                    <pre class="overflow-x-auto rounded-lg border border-blue-200 bg-white p-3 text-xs dark:border-blue-500/35 dark:bg-surface-900">{{ formatJson(log.request_headers) }}</pre>
                  </div>
                  <div v-if="log.request_body">
                    <h5 class="mb-2 text-xs font-medium text-blue-800 dark:text-blue-300">Request Body:</h5>
                    <pre class="max-h-60 overflow-x-auto overflow-y-auto rounded-lg border border-blue-200 bg-white p-3 text-xs dark:border-blue-500/35 dark:bg-surface-900">{{ formatJson(log.request_body) }}</pre>
                  </div>
                </div>

                <div v-if="log.response_status || log.response_body" class="border-b border-green-200 bg-green-50 p-4 dark:border-green-500/35 dark:bg-green-500/10">
                  <h4 class="mb-3 font-semibold text-green-900 dark:text-green-200">响应信息</h4>
                  <div v-if="log.response_status" class="mb-3">
                    <Tag :severity="getHttpStatusSeverity(log.response_status)">
                      HTTP {{ log.response_status }}
                    </Tag>
                  </div>
                  <div v-if="log.response_body">
                    <h5 class="mb-2 text-xs font-medium text-green-800 dark:text-green-300">Response Body:</h5>
                    <pre class="max-h-60 overflow-x-auto overflow-y-auto rounded-lg border border-green-200 bg-white p-3 text-xs dark:border-green-500/35 dark:bg-surface-900">{{ formatJson(log.response_body) }}</pre>
                  </div>
                </div>

                <div v-if="log.pipeline_trace?.steps?.length" class="border-b border-amber-200 bg-amber-50 p-4 dark:border-amber-500/35 dark:bg-amber-500/10">
                  <h4 class="mb-3 font-semibold text-amber-900 dark:text-amber-200">
                    处理链路 ({{ log.pipeline_trace.step_count }} 步, {{ formatDuration(log.pipeline_trace.total_duration_ms) }})
                  </h4>
                  <div class="mb-3 flex items-center gap-2">
                    <Tag severity="success">成功 {{ log.pipeline_stats?.ok || 0 }}</Tag>
                    <Tag severity="warn">警告 {{ log.pipeline_stats?.warning || 0 }}</Tag>
                    <Tag severity="danger">失败 {{ log.pipeline_stats?.error || 0 }}</Tag>
                  </div>
                  <div class="relative ml-3">
                    <div class="absolute bottom-2 left-[5px] top-2 w-px bg-amber-300 dark:bg-amber-500/35"></div>
                    <div
                      v-for="(step, i) in log.pipeline_trace.steps"
                      :key="i"
                      class="relative pb-3 pl-6 last:pb-0"
                    >
                      <div class="flex items-center gap-2">
                        <span
                          class="absolute left-0 text-xs leading-none"
                          :class="getStepDotClass(step.status)"
                        >●</span>
                        <span class="font-mono text-xs text-amber-700 dark:text-amber-300">#{{ i + 1 }}</span>
                        <span class="font-mono edium text-amber-900 dark:text-amber-100">{{ stepLabel(step.name) }}</span>
                        <span v-if="step.duration_ms" class="text-xs text-gray-500 dark:text-surface-400">{{ formatDuration(step.duration_ms) }}</span>
                        <span v-if="step.ts" class="text-xs text-gray-400 dark:text-surface-500">{{ formatStepTime(step.ts) }}</span>
                        <Tag :severity="getStepStatusSeverity(step.status)">
                          {{ getStepStatusLabel(step.status) }}
                        </Tag>
                      </div>
                      <div v-if="step.data" class="mt-1">
                        <pre
                          class="max-h-64 overflow-x-auto overflow-y-auto whitespace-pre-wrap break-all rounded-lg border border-amber-200 bg-white p-3 text-xs dark:border-amber-500/35 dark:bg-surface-900"
                        ><code>{{ formatStepData(step.name, step.data) }}</code></pre>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else-if="log.processing_details" class="border-b border-amber-200 bg-amber-50 p-4 dark:border-amber-500/35 dark:bg-amber-500/10">
                  <h4 class="mb-3 font-semibold text-amber-900 dark:text-amber-200">处理详情</h4>
                  <pre class="max-h-60 overflow-x-auto overflow-y-auto rounded-lg border border-amber-200 bg-white p-3 text-xs dark:border-amber-500/35 dark:bg-surface-900">{{ formatJson(log.processing_details) }}</pre>
                </div>

                <div v-if="log.skip_reason" class="bg-amber-50 p-4 dark:bg-amber-500/10">
                  <h4 class="mb-2 font-semibold text-amber-900 dark:text-amber-200">跳过原因</h4>
                  <pre class="overflow-x-auto rounded-lg border border-amber-200 bg-amber-100 p-3 text-xs text-amber-800 dark:border-amber-500/35 dark:bg-amber-500/15 dark:text-amber-200">{{ log.skip_reason }}</pre>
                </div>

                <div v-if="log.error_message" class="bg-red-50 p-4 dark:bg-red-500/10">
                  <h4 class="mb-2 font-semibold text-red-900 dark:text-red-200">错误信息</h4>
                  <pre class="overflow-x-auto rounded-lg border border-red-200 bg-red-100 p-3 text-xs text-red-800 dark:border-red-500/35 dark:bg-red-500/15 dark:text-red-200">{{ log.error_message }}</pre>
                </div>

                <div v-if="log.details && !log.request_headers && !log.request_body" class="p-4">
                  <h4 class="mb-2 font-semibold text-surface-900 dark:text-surface-100">详细信息</h4>
                  <pre class="max-h-60 overflow-x-auto overflow-y-auto rounded-lg bg-surface-900 p-3 text-xs text-surface-100">{{ log.details }}</pre>
                </div>
              </div>
            </div>
          </template>
          <div
            v-else
            class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-8 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/60 dark:text-surface-400"
          >
            暂无日志
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RefreshCw, Trash2 } from 'lucide-vue-next'
import { getLogs } from '@/api/index'
import { formatBackendDateTime, formatBackendTime } from '@/utils/datetime'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'

const logLevel = ref('all')
const loading = ref(false)
const expandedLogs = ref<Record<number, boolean>>({})
const logsList = ref<any[]>([])
const logLevelOptions = [
  { label: '全部', value: 'all' },
  { label: 'INFO', value: 'info' },
  { label: 'WARNING', value: 'warning' },
  { label: 'ERROR', value: 'error' },
]

const filteredLogs = computed(() => {
  if (logLevel.value === 'all') return logsList.value
  return logsList.value.filter(log => log.level?.toLowerCase() === logLevel.value.toLowerCase())
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = logLevel.value !== 'all' ? { level: logLevel.value } : {}
    const response: any = await getLogs(params)
    const items = response?.results || []
    logsList.value = items.map((item: any) => {
      const pipelineTrace = normalizePipelineTrace(item.pipeline_trace)
      return {
        ...item,
        pipeline_trace: pipelineTrace,
        level: item.log_level || 'INFO',
        timestamp: formatDisplayTime(item.created_at),
        message: item.skip_reason || item.error_message || `${item.event_type} from ${item.project_name}`,
        request_body: item.request_body_raw ? tryParseJson(item.request_body_raw) : item.payload,
        pipeline_stats: getPipelineStats(pipelineTrace),
      }
    })
  } catch (error) {
    console.error('获取日志记录失败:', error)
  } finally {
    loading.value = false
  }
}

watch(logLevel, () => {
  fetchLogs()
})

onMounted(() => {
  fetchLogs()
})

const getLogSeverity = (level: string) => {
  const value = String(level || '').toUpperCase()
  if (value === 'ERROR') return 'danger'
  if (value === 'WARNING') return 'warn'
  if (value === 'INFO') return 'info'
  return 'secondary'
}

const toggleDetails = (index: number) => {
  expandedLogs.value[index] = !expandedLogs.value[index]
}

const formatJson = (data: any) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch (e) {
    return data
  }
}

const tryParseJson = (str: string) => {
  try { return JSON.parse(str) } catch { return str }
}

const stepLabelMap: Record<string, string> = {
  project_found: '项目匹配',
  event_rule_unmatched: '事件规则未命中',
  event_rule_matched: '事件规则匹配',
  project_review_disabled: '项目审查已禁用',
  mr_context_parsed: '解析 MR 上下文',
  review_record_created: '创建审查记录',
  provider_resolved: 'LLM 供应商解析',
  mock_mode_skip_llm: 'Mock 模式跳过 LLM',
  clone_repository: '克隆仓库',
  checkout_branch: '检出分支',
  commit_range: '计算提交范围',
  custom_prompt_resolved: '加载自定义提示词',
  llm_request_payload: 'LLM 请求数据',
  llm_review: 'LLM 审查',
  llm_response_payload: 'LLM 返回数据',
  get_mr_changes: '获取 MR 变更',
  changes_fetched: '变更文件统计',
  changes_filtered: '变更过滤明细',
  review_result_ready: '审查结果汇总',
  report_generated: '生成审查报告',
  notification_dispatched: '通知分发汇总',
  notification_result_details: '通知分发明细',
  notification_dispatch: '通知分发',
  pipeline_failed: '处理链路失败',
}

const stepLabel = (name: string) => {
  if (typeof name === 'string' && name.startsWith('notification_dispatch:')) {
    return `通知分发:${name.slice('notification_dispatch:'.length)}`
  }
  return stepLabelMap[name] || name
}

const normalizePipelineTrace = (trace: any) => {
  if (!trace || typeof trace !== 'object') return { steps: [], step_count: 0, total_duration_ms: 0 }
  const steps = Array.isArray(trace.steps) ? trace.steps : []
  return {
    ...trace,
    steps,
    step_count: typeof trace.step_count === 'number' ? trace.step_count : steps.length,
    total_duration_ms: typeof trace.total_duration_ms === 'number' ? trace.total_duration_ms : 0,
  }
}

const getPipelineStats = (trace: any) => {
  const steps = Array.isArray(trace?.steps) ? trace.steps : []
  return steps.reduce((acc: { ok: number; warning: number; error: number }, step: any) => {
    const status = String(step?.status || 'ok')
    if (status === 'error') acc.error += 1
    else if (status === 'warning') acc.warning += 1
    else acc.ok += 1
    return acc
  }, { ok: 0, warning: 0, error: 0 })
}

const getStepStatusLabel = (status: string) => {
  if (status === 'error') return '失败'
  if (status === 'warning') return '警告'
  return '成功'
}

const getStepStatusSeverity = (status: string) => {
  if (status === 'error') return 'danger'
  if (status === 'warning') return 'warn'
  return 'success'
}

const getStepDotClass = (status: string) => {
  if (status === 'error') return 'text-red-500 dark:text-red-300'
  if (status === 'warning') return 'text-orange-500 dark:text-orange-300'
  return 'text-green-500 dark:text-green-300'
}

const formatStepValue = (value: any, maxLength: number = 200, truncate: boolean = true) => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') {
    if (!truncate) return value
    return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
  }
  try {
    const text = JSON.stringify(value)
    if (!truncate) return text
    return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
  } catch (e) {
    return String(value)
  }
}

const parseSampleList = (value: any) => {
  if (value === null || value === undefined) return []
  const text = String(value).trim()
  if (!text || text === '-') return []
  return text.split(',').map(item => item.trim()).filter(Boolean)
}

const formatChangesFilteredData = (data: Record<string, any>) => {
  const lines = [
    `raw_file_count: ${formatStepValue(data.raw_file_count)}`,
    `filtered_file_count: ${formatStepValue(data.filtered_file_count)}`,
    `removed_file_count: ${formatStepValue(data.removed_file_count)}`,
    `excluded_by_type_count: ${formatStepValue(data.excluded_by_type_count)}`,
    `ignored_by_pattern_count: ${formatStepValue(data.ignored_by_pattern_count)}`,
    `deleted_file_count: ${formatStepValue(data.deleted_file_count)}`,
    `renamed_without_diff_count: ${formatStepValue(data.renamed_without_diff_count)}`,
  ]

  const excludedSample = parseSampleList(data.excluded_by_type_sample)
  lines.push('excluded_by_type_sample:')
  if (excludedSample.length) {
    excludedSample.forEach((item, idx) => lines.push(`  ${idx + 1}. ${item}`))
  } else {
    lines.push('  -')
  }

  const ignoredSample = parseSampleList(data.ignored_by_pattern_sample)
  lines.push('ignored_by_pattern_sample:')
  if (ignoredSample.length) {
    ignoredSample.forEach((item, idx) => lines.push(`  ${idx + 1}. ${item}`))
  } else {
    lines.push('  -')
  }

  return lines.join('\n')
}

const tryParseJsonString = (value: any) => {
  if (typeof value !== 'string') return null
  try {
    return JSON.parse(value)
  } catch (e) {
    return null
  }
}

const formatNotificationResultDetailsData = (data: Record<string, any>) => {
  const lines = [
    `total_channels: ${formatStepValue(data.total_channels)}`,
    `success_channels: ${formatStepValue(data.success_channels)}`,
    `failed_channels: ${formatStepValue(data.failed_channels)}`,
  ]
  const details = tryParseJsonString(data.channels_detail)
  lines.push('channels_detail:')
  if (Array.isArray(details) && details.length) {
    details.forEach((item: any, idx: number) => {
      const status = item?.success ? 'SUCCESS' : 'FAILED'
      const channelName = formatStepValue(item?.channel_name || item?.channel || '-')
      const message = formatStepValue(item?.message || '-', 200, false)
      const responseTime = formatStepValue(item?.response_time)
      const statusCode = formatStepValue(item?.status_code)
      lines.push(`  ${idx + 1}. [${status}] ${channelName}`)
      lines.push(`     message: ${message}`)
      lines.push(`     response_time: ${responseTime}`)
      lines.push(`     status_code: ${statusCode}`)
    })
  } else {
    const raw = formatStepValue(data.channels_detail, 4000, false)
    lines.push(`  ${raw === '-' ? '-' : raw}`)
  }
  if (data.channels_detail_truncated) {
    lines.push('  ... (truncated)')
  }
  return lines.join('\n')
}

const formatNotificationDispatchChannelData = (data: Record<string, any>) => {
  const lines = [
    `channel: ${formatStepValue(data.channel)}`,
    `channel_name: ${formatStepValue(data.channel_name)}`,
    `success: ${formatStepValue(data.success)}`,
    `message: ${formatStepValue(data.result_message ?? data.message, 400, false)}`,
    `response_time: ${formatStepValue(data.response_time)}`,
    `status_code: ${formatStepValue(data.status_code)}`,
  ]

  const requestParsed = tryParseJsonString(data.request)
  lines.push('request:')
  if (requestParsed && typeof requestParsed === 'object') {
    lines.push(
      ...JSON.stringify(requestParsed, null, 2)
        .split('\n')
        .map(line => `  ${line}`)
    )
  } else {
    lines.push(`  ${formatStepValue(data.request, 1000, false)}`)
  }
  if (data.request_truncated) {
    lines.push('  ... (truncated)')
  }

  const responseParsed = tryParseJsonString(data.response)
  lines.push('response:')
  if (responseParsed && typeof responseParsed === 'object') {
    lines.push(
      ...JSON.stringify(responseParsed, null, 2)
        .split('\n')
        .map(line => `  ${line}`)
    )
  } else {
    lines.push(`  ${formatStepValue(data.response, 1000, false)}`)
  }
  if (data.response_truncated) {
    lines.push('  ... (truncated)')
  }

  return lines.join('\n')
}

const formatLLMPayloadData = (data: Record<string, any>) => {
  const lines: string[] = []
  Object.entries(data).forEach(([key, value]) => {
    if (typeof value === 'string' && value.includes('\n')) {
      lines.push(`${key}:`)
      lines.push(value)
      return
    }
    lines.push(`${key}: ${formatStepValue(value, 200, false)}`)
  })
  return lines.join('\n')
}

const formatStepData = (stepName: string, data: any) => {
  if (!data || typeof data !== 'object') return formatStepValue(data)
  if (stepName === 'changes_filtered') return formatChangesFilteredData(data as Record<string, any>)
  if (stepName === 'notification_result_details') return formatNotificationResultDetailsData(data as Record<string, any>)
  if (typeof stepName === 'string' && stepName.startsWith('notification_dispatch:')) {
    return formatNotificationDispatchChannelData(data as Record<string, any>)
  }
  if (stepName === 'llm_request_payload' || stepName === 'llm_response_payload') {
    return formatLLMPayloadData(data as Record<string, any>)
  }
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${formatStepValue(value)}`)
    .join('\n')
}

const formatStepTime = (value: string) => {
  return formatBackendTime(value)
}

const formatDisplayTime = (value: string | null | undefined): string => {
  return formatBackendDateTime(value)
}

const formatDuration = (ms: number) => {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const getHttpStatusSeverity = (status: number) => {
  if (status < 300) return 'success'
  if (status < 400) return 'warn'
  return 'danger'
}

const handleRefresh = () => {
  fetchLogs()
}

const handleClear = () => {
  const confirmed = window.confirm('确定要清空所有日志吗？')
  if (!confirmed) return
  logsList.value = []
  expandedLogs.value = {}
}
</script>
