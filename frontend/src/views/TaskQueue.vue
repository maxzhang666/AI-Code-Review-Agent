<template>
  <div class="mx-auto w-full max-w-[1800px] space-y-4">
    <section class="rounded-2xl border border-surface-200/70 bg-gradient-to-r from-surface-50 via-surface-0 to-primary-50/30 px-4 py-4 shadow-sm dark:border-surface-700/70 dark:from-surface-900/80 dark:via-surface-900 dark:to-primary-900/20">
      <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div class="space-y-0.5">
          <h2 class="text-xl font-bold tracking-tight text-surface-900 dark:text-surface-0">任务队列</h2>
          <p class="text-xs text-surface-600 dark:text-surface-300">统一观察异步任务状态、失败原因与执行事件时间线</p>
        </div>

        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">待处理</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ statusCount('pending') }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">处理中</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ statusCount('processing') }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">已完成</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ statusCount('completed') }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">失败</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ statusCount('failed') }}</p>
          </div>
        </div>
      </div>
    </section>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="grid gap-2 lg:grid-cols-2">
          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
            <p class="text-xs font-medium text-surface-700 dark:text-surface-200">任务执行态</p>
            <p class="mt-1 text-sm text-surface-900 dark:text-surface-0">
              backend：<span class="font-semibold">{{ queueBackendLabel }}</span>，
              持久化：<span class="font-semibold">{{ queuePersistenceLabel }}</span>
            </p>
            <p class="mt-1 text-[11px] text-surface-500 dark:text-surface-400">memory backend 下任务执行态不会持久化。</p>
          </div>

          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
            <p class="text-xs font-medium text-surface-700 dark:text-surface-200">观测数据持久化</p>
            <p class="mt-1 text-sm text-surface-900 dark:text-surface-0">{{ observabilityPersistenceLabel }}</p>
            <p class="mt-1 text-[11px] text-surface-500 dark:text-surface-400">与 queue backend 解耦，由观测写入目标是否可用决定。</p>
          </div>
        </div>
      </template>
    </Card>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="space-y-3">
          <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div class="inline-flex items-center gap-2 text-xs font-medium text-surface-700 dark:text-surface-200">
              <span class="inline-flex h-2 w-2 rounded-full bg-primary-500" />
              查询筛选
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <div class="inline-flex items-center gap-2 rounded-md border border-surface-200 px-2.5 py-1.5 dark:border-surface-700">
                <span class="text-xs text-surface-500 dark:text-surface-400">自动刷新</span>
                <ToggleSwitch v-model="autoRefresh" />
              </div>
              <Button label="手动刷新" outlined size="small" :loading="loadingList" @click="handleRefresh" />
              <Button label="重置筛选" outlined size="small" :disabled="loadingList" @click="resetFilters" />
              <Button label="查询任务" size="small" :loading="loadingList" @click="applyFilters" />
            </div>
          </div>

          <div class="rounded-xl border border-surface-200/70 bg-surface-50/45 p-2.5 dark:border-surface-700/60 dark:bg-surface-800/25">
            <div class="grid grid-cols-1 gap-2 md:grid-cols-2 xl:[grid-template-columns:0.9fr_1fr_1.2fr_1.2fr_1.4fr]">
              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">状态</span>
                <Select
                  v-model="filters.status"
                  :options="statusOptions"
                  option-label="label"
                  option-value="value"
                  class="w-full"
                  placeholder="全部状态"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">任务类型</span>
                <InputText v-model="filters.taskType" class="w-full" placeholder="如 generate_developer_weekly_snapshot" />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">Task ID</span>
                <InputText v-model="filters.taskId" class="w-full" placeholder="输入 task_id 精确定位" />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">Run ID</span>
                <InputText v-model="filters.runId" class="w-full" placeholder="按同一次调度 run_id 聚合查看" />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">创建时间范围</span>
                <DatePicker
                  v-model="filters.createdRange"
                  selectionMode="range"
                  dateFormat="yy-mm-dd"
                  showIcon
                  iconDisplay="input"
                  class="w-full"
                  placeholder="选择开始与结束日期"
                />
              </label>
            </div>
          </div>

          <div v-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 dark:border-red-500/40 dark:bg-red-500/15 dark:text-red-200">
            {{ errorMessage }}
          </div>
        </div>
      </template>
    </Card>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm font-medium text-surface-700 dark:text-surface-200">
            周报调度决策日志
            <span class="ml-2 text-xs font-normal text-surface-500 dark:text-surface-400">
              共 {{ schedulerLogsTotal }} 条，第 {{ schedulerLogsPage }} / {{ schedulerLogsTotalPages }} 页
            </span>
          </div>
          <Button label="刷新日志" size="small" text :loading="schedulerLogsLoading" @click="fetchSchedulerLogs" />
        </div>

        <div class="relative max-h-[460px] overflow-auto rounded-xl border border-surface-200/70 dark:border-surface-700/70">
          <table class="w-full min-w-[1200px] text-sm text-surface-800 dark:text-surface-100">
            <thead>
              <tr class="sticky top-0 z-[1] border-b border-surface-200/70 bg-surface-50/95 text-left text-xs font-semibold uppercase tracking-wide text-surface-600 backdrop-blur dark:border-surface-600/70 dark:bg-surface-800/95 dark:text-surface-200">
                <th class="px-2 py-2.5 whitespace-nowrap">时间</th>
                <th class="px-2 py-2.5 whitespace-nowrap">状态</th>
                <th class="px-2 py-2.5 whitespace-nowrap">原因</th>
                <th class="px-2 py-2.5 whitespace-nowrap">Run ID</th>
                <th class="px-2 py-2.5 whitespace-nowrap">Task ID</th>
                <th class="px-2 py-2.5 whitespace-nowrap">周起始</th>
                <th class="px-2 py-2.5 whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="schedulerLogs.length === 0">
                <td colspan="7" class="px-3 py-5 text-center text-sm text-surface-500 dark:text-surface-400">暂无调度决策日志</td>
              </tr>
              <tr
                v-for="log in schedulerLogs"
                :key="log.id"
                class="border-b border-surface-100/80 align-top transition hover:bg-surface-50/70 dark:border-surface-700/70 dark:hover:bg-surface-700/55"
              >
                <td class="px-2 py-2.5 whitespace-nowrap text-xs">{{ formatDateTime(log.created_at) }}</td>
                <td class="px-2 py-2.5 whitespace-nowrap"><Tag :severity="schedulerStatusSeverity(log.status)">{{ log.status || '-' }}</Tag></td>
                <td class="px-2 py-2.5 whitespace-nowrap text-xs">{{ schedulerReasonLabel(log.reason) }}</td>
                <td class="px-2 py-2.5"><div class="max-w-[280px] truncate font-mono text-xs" :title="log.run_id || '-'">{{ log.run_id || '-' }}</div></td>
                <td class="px-2 py-2.5"><div class="max-w-[280px] truncate font-mono text-xs" :title="log.task_id || '-'">{{ log.task_id || '-' }}</div></td>
                <td class="px-2 py-2.5 whitespace-nowrap text-xs">{{ log.week_start || '-' }}</td>
                <td class="px-2 py-2.5 whitespace-nowrap">
                  <Button
                    label="筛选同次运行"
                    size="small"
                    text
                    :disabled="!log.run_id"
                    @click="filterByRunId(log.run_id)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-3 flex items-center justify-end gap-2">
          <Button
            label="上一页"
            size="small"
            text
            :disabled="schedulerLogsPage <= 1 || schedulerLogsLoading"
            @click="goPrevSchedulerLogsPage"
          />
          <Button
            label="下一页"
            size="small"
            text
            :disabled="schedulerLogsPage >= schedulerLogsTotalPages || schedulerLogsLoading"
            @click="goNextSchedulerLogsPage"
          />
        </div>
      </template>
    </Card>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm font-medium text-surface-700 dark:text-surface-200">
            任务列表
            <span class="ml-2 text-xs font-normal text-surface-500 dark:text-surface-400">共 {{ total }} 条</span>
          </div>
          <div class="text-xs text-surface-500 dark:text-surface-400">每页 {{ limit }} 条，第 {{ page }} / {{ totalPages }} 页</div>
        </div>

        <div class="relative overflow-auto rounded-xl border border-surface-200/70 dark:border-surface-700/70">
          <table class="w-full min-w-[1620px] text-sm text-surface-800 dark:text-surface-100">
            <thead>
              <tr class="sticky top-0 z-[1] border-b border-surface-200/70 bg-surface-50/95 text-left text-xs font-semibold uppercase tracking-wide text-surface-600 backdrop-blur dark:border-surface-600/70 dark:bg-surface-800/95 dark:text-surface-200">
                <th class="px-2 py-3 whitespace-nowrap">Task ID</th>
                <th class="px-2 py-3 whitespace-nowrap">Run ID</th>
                <th class="px-2 py-3 whitespace-nowrap">类型</th>
                <th class="px-2 py-3 whitespace-nowrap">状态</th>
                <th class="px-2 py-3 whitespace-nowrap">重试</th>
                <th class="px-2 py-3 whitespace-nowrap">创建时间</th>
                <th class="px-2 py-3 whitespace-nowrap">开始时间</th>
                <th class="px-2 py-3 whitespace-nowrap">完成时间</th>
                <th class="px-2 py-3 whitespace-nowrap">耗时</th>
                <th class="min-w-[220px] px-2 py-3">错误摘要</th>
                <th class="px-2 py-3 text-right whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loadingList">
                <td colspan="11" class="px-3 py-6 text-center text-sm text-surface-500 dark:text-surface-400">正在加载任务...</td>
              </tr>
              <tr v-else-if="tasks.length === 0">
                <td colspan="11" class="px-3 py-6 text-center text-sm text-surface-500 dark:text-surface-400">暂无任务数据</td>
              </tr>
              <tr
                v-for="task in tasks"
                :key="task.task_id"
                class="border-b border-surface-100/80 align-top transition hover:bg-surface-50/70 dark:border-surface-700/70 dark:hover:bg-surface-700/55"
              >
                <td class="px-2 py-3">
                  <div class="max-w-[260px] truncate font-mono text-xs" :title="task.task_id">{{ task.task_id }}</div>
                </td>
                <td class="px-2 py-3">
                  <div class="max-w-[260px] truncate font-mono text-xs" :title="task.run_id || '-'">{{ task.run_id || '-' }}</div>
                </td>
                <td class="px-2 py-3"><div class="max-w-[260px] truncate" :title="task.task_type || '-'">{{ task.task_type || '-' }}</div></td>
                <td class="px-2 py-3 whitespace-nowrap">
                  <Tag :severity="statusSeverity(task.status)">{{ statusLabel(task.status) }}</Tag>
                </td>
                <td class="px-2 py-3 whitespace-nowrap text-xs text-surface-700 dark:text-surface-200">
                  {{ task.retry_count ?? 0 }} / {{ task.max_retries ?? 0 }}
                </td>
                <td class="px-2 py-3 whitespace-nowrap text-xs text-surface-700 dark:text-surface-200">{{ formatDateTime(task.created_at) }}</td>
                <td class="px-2 py-3 whitespace-nowrap text-xs text-surface-700 dark:text-surface-200">{{ formatDateTime(task.started_at) }}</td>
                <td class="px-2 py-3 whitespace-nowrap text-xs text-surface-700 dark:text-surface-200">{{ formatDateTime(task.completed_at) }}</td>
                <td class="px-2 py-3 whitespace-nowrap text-xs text-surface-700 dark:text-surface-200">{{ formatDuration(task) }}</td>
                <td class="px-2 py-3"><p class="line-clamp-2 text-xs text-red-600 dark:text-red-300">{{ task.error_message || '-' }}</p></td>
                <td class="px-2 py-3 text-right whitespace-nowrap">
                  <Button label="详情" size="small" outlined @click="openTaskDetail(task.task_id)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-3 flex items-center justify-end gap-2">
          <Button label="上一页" size="small" text :disabled="page <= 1 || loadingList" @click="goPrevPage" />
          <Button label="下一页" size="small" text :disabled="page >= totalPages || loadingList" @click="goNextPage" />
        </div>
      </template>
    </Card>

    <Drawer v-model:visible="detailVisible" position="right" class="w-[96vw] max-w-[1120px]">
      <template #header>
        <div class="space-y-1">
          <p class="text-sm text-surface-500 dark:text-surface-400">任务详情</p>
          <h3 class="max-w-[980px] truncate font-mono text-sm font-semibold">{{ detailTask?.task_id || '-' }}</h3>
        </div>
      </template>

      <div v-if="loadingDetail" class="py-8 text-center text-sm text-surface-500 dark:text-surface-400">加载中...</div>
      <div v-else-if="!detailTask" class="py-8 text-center text-sm text-surface-500 dark:text-surface-400">暂无详情数据</div>
      <div v-else class="space-y-4">
        <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900/60">
          <div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
            <div>
              <span class="text-surface-500 dark:text-surface-400">状态：</span>
              <Tag :severity="statusSeverity(detailTask.status)">{{ statusLabel(detailTask.status) }}</Tag>
            </div>
            <div><span class="text-surface-500 dark:text-surface-400">任务类型：</span>{{ detailTask.task_type || '-' }}</div>
            <div><span class="text-surface-500 dark:text-surface-400">Run ID：</span><span class="font-mono text-xs">{{ detailTask.run_id || '-' }}</span></div>
            <div><span class="text-surface-500 dark:text-surface-400">重试：</span>{{ detailTask.retry_count ?? 0 }} / {{ detailTask.max_retries ?? 0 }}</div>
            <div><span class="text-surface-500 dark:text-surface-400">耗时：</span>{{ formatDuration(detailTask) }}</div>
            <div><span class="text-surface-500 dark:text-surface-400">创建：</span>{{ formatDateTime(detailTask.created_at) }}</div>
            <div><span class="text-surface-500 dark:text-surface-400">完成：</span>{{ formatDateTime(detailTask.completed_at) }}</div>
          </div>
        </div>

        <div class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
          <div class="mb-2 flex items-center justify-between">
            <h4 class="text-sm font-medium">业务链路</h4>
            <Tag severity="secondary">steps {{ taskTraceSteps.length }}</Tag>
          </div>
          <ol class="space-y-2">
            <li v-if="taskTraceSteps.length === 0" class="text-xs text-surface-500 dark:text-surface-400">当前任务无业务 trace_steps</li>
            <li
              v-for="(step, index) in taskTraceSteps"
              :key="`${step.name || 'step'}-${index}-${step.at || step.ts || ''}`"
              class="rounded-md border border-surface-200/70 bg-surface-0 p-2 dark:border-surface-700/70 dark:bg-surface-950/60"
            >
              <div class="flex flex-wrap items-center gap-2 text-xs">
                <Tag severity="info">{{ step.name || '-' }}</Tag>
                <Tag :severity="step.status === 'warning' ? 'warn' : step.status === 'error' ? 'danger' : 'success'">{{ step.status || 'ok' }}</Tag>
                <span v-if="typeof step.duration_ms === 'number'" class="text-surface-500 dark:text-surface-400">{{ Math.round(step.duration_ms) }}ms</span>
                <span class="ml-auto text-surface-500 dark:text-surface-400">{{ formatDateTime(step.at || step.ts) }}</span>
              </div>
              <details v-if="step.data" class="mt-1">
                <summary class="cursor-pointer text-xs text-primary">查看步骤数据</summary>
                <pre class="mt-1 max-h-[220px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ jsonPreview(step.data) }}</pre>
              </details>
            </li>
          </ol>
        </div>

        <details class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
          <summary class="cursor-pointer text-sm font-medium">Payload</summary>
          <pre class="mt-2 max-h-[280px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ jsonPreview(detailTask.payload) }}</pre>
        </details>

        <details class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
          <summary class="cursor-pointer text-sm font-medium">Result</summary>
          <pre class="mt-2 max-h-[280px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ jsonPreview(detailTask.result) }}</pre>
        </details>

        <details class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
          <summary class="cursor-pointer text-sm font-medium">Error</summary>
          <pre class="mt-2 max-h-[280px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ detailTask.error_message || '-' }}</pre>
        </details>

        <div class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-900/55">
          <div class="mb-2 flex items-center justify-between">
            <h4 class="text-sm font-medium">事件时间线</h4>
            <Button label="刷新事件" size="small" text @click="refreshDetailEvents" />
          </div>
          <ol class="space-y-2">
            <li v-if="detailEvents.length === 0" class="text-xs text-surface-500 dark:text-surface-400">暂无事件</li>
            <li v-for="event in detailEvents" :key="event.id || `${event.event_type}-${event.created_at}-${event.attempt_no}`" class="rounded-md border border-surface-200/70 bg-surface-0 p-2 dark:border-surface-700/70 dark:bg-surface-950/60">
              <div class="flex flex-wrap items-center gap-2 text-xs">
                <Tag severity="info">{{ event.event_type || '-' }}</Tag>
                <Tag :severity="statusSeverity(event.status_after)">{{ statusLabel(event.status_after) }}</Tag>
                <span class="text-surface-500 dark:text-surface-400">attempt #{{ event.attempt_no ?? '-' }}</span>
                <span class="ml-auto text-surface-500 dark:text-surface-400">{{ formatDateTime(event.created_at) }}</span>
              </div>
              <p v-if="event.message" class="mt-1 text-xs text-surface-700 dark:text-surface-200">{{ event.message }}</p>
              <details v-if="event.event_payload" class="mt-1">
                <summary class="cursor-pointer text-xs text-primary">查看事件载荷</summary>
                <pre class="mt-1 max-h-[220px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ jsonPreview(event.event_payload) }}</pre>
              </details>
            </li>
          </ol>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  getSystemTaskDetail,
  getSystemTaskEvents,
  getSystemTaskSummary,
  getSystemTasks,
  getWeeklySchedulerLogs,
  type SystemTaskDetailResponse,
  type SystemTaskEventItem,
  type SystemTaskObservationItem,
  type SystemTaskSummaryResponse,
  type WeeklySchedulerLogItem,
} from '@/api/index'
import Button from 'primevue/button'
import Card from 'primevue/card'
import DatePicker from 'primevue/datepicker'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

interface TaskQueueFilters {
  status: string
  taskType: string
  taskId: string
  runId: string
  createdRange: Date[] | null
}

const route = useRoute()

const summary = ref<SystemTaskSummaryResponse>({})
const tasks = ref<SystemTaskObservationItem[]>([])
const schedulerLogs = ref<WeeklySchedulerLogItem[]>([])
const schedulerLogsTotal = ref(0)
const schedulerLogsPage = ref(1)
const schedulerLogsLimit = ref(20)
const total = ref(0)
const page = ref(1)
const limit = ref(20)

const loadingList = ref(false)
const schedulerLogsLoading = ref(false)
const loadingDetail = ref(false)
const errorMessage = ref('')

const detailVisible = ref(false)
const detailTask = ref<SystemTaskDetailResponse | null>(null)
const detailEvents = ref<SystemTaskEventItem[]>([])

const autoRefresh = ref(true)
let autoRefreshTimer: number | null = null

const filters = reactive<TaskQueueFilters>({
  status: '',
  taskType: '',
  taskId: '',
  runId: '',
  createdRange: null,
})

const statusOptions = [
  { label: '全部', value: '' },
  { label: 'pending', value: 'pending' },
  { label: 'processing', value: 'processing' },
  { label: 'completed', value: 'completed' },
  { label: 'failed', value: 'failed' },
  { label: 'retrying', value: 'retrying' },
]

const queueBackendLabel = computed(() => String(summary.value.queue_backend || 'unknown'))
const queuePersistenceLabel = computed(() => {
  const value = summary.value.is_persistent
  if (value === true) return '是'
  if (value === false) return '否'
  return '未知'
})

const observabilityPersistenceLabel = computed(() => {
  const value = summary.value.observability_persistent
  if (value === true) return '是'
  if (value === false) return '否'
  return '后端未显式返回（默认按可用性观测）'
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)))
const schedulerLogsTotalPages = computed(() => Math.max(1, Math.ceil(schedulerLogsTotal.value / schedulerLogsLimit.value)))

const statusCount = (status: string) => Number(summary.value.by_status?.[status] || 0)

interface TaskTraceStep {
  name: string
  status?: string
  at?: string | null
  ts?: string | null
  duration_ms?: number | null
  data?: Record<string, any> | null
}

const taskTraceSteps = computed<TaskTraceStep[]>(() => {
  const raw = detailTask.value?.result
  if (!raw || typeof raw !== 'object') return []
  const steps = (raw as Record<string, unknown>).trace_steps
  return Array.isArray(steps) ? (steps as TaskTraceStep[]) : []
})

const normalizeEvents = (payload: unknown): SystemTaskEventItem[] => {
  if (Array.isArray(payload)) return payload as SystemTaskEventItem[]
  if (payload && typeof payload === 'object') {
    const candidate = payload as { results?: unknown; events?: unknown }
    if (Array.isArray(candidate.results)) return candidate.results as SystemTaskEventItem[]
    if (Array.isArray(candidate.events)) return candidate.events as SystemTaskEventItem[]
  }
  return []
}

const toIso = (value: Date, endOfDay: boolean): string => {
  const copy = new Date(value)
  if (endOfDay) {
    copy.setHours(23, 59, 59, 999)
  } else {
    copy.setHours(0, 0, 0, 0)
  }
  return copy.toISOString()
}

const buildListParams = () => {
  const params: Record<string, any> = {
    page: page.value,
    limit: limit.value,
  }

  const status = filters.status.trim()
  const taskType = filters.taskType.trim()
  const taskId = filters.taskId.trim()
  const runId = filters.runId.trim()
  if (status) params.status = status
  if (taskType) params.task_type = taskType
  if (taskId) params.task_id = taskId
  if (runId) params.run_id = runId

  if (Array.isArray(filters.createdRange) && filters.createdRange[0] instanceof Date) {
    params.created_from = toIso(filters.createdRange[0], false)
    if (filters.createdRange[1] instanceof Date) {
      params.created_to = toIso(filters.createdRange[1], true)
    }
  }

  return params
}

const formatDateTime = (value?: string | null): string => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

const statusSeverity = (status?: string | null): 'info' | 'warn' | 'success' | 'danger' | 'secondary' => {
  switch (status) {
    case 'pending':
      return 'secondary'
    case 'processing':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'retrying':
      return 'warn'
    default:
      return 'secondary'
  }
}

const statusLabel = (status?: string | null): string => {
  if (!status) return '-'
  return status
}

const schedulerStatusSeverity = (status?: string | null): 'info' | 'warn' | 'success' | 'danger' | 'secondary' => {
  if (status === 'queued') return 'success'
  if (status === 'skipped') return 'warn'
  if (status === 'error') return 'danger'
  return 'secondary'
}

const schedulerReasonLabel = (reason?: string | null): string => {
  if (!reason) return '-'
  const map: Record<string, string> = {
    disabled: '调度未启用',
    not_trigger_time: '未到触发时间',
    already_enqueued: '本周已入队',
  }
  return map[reason] || reason
}

const formatDuration = (task: Pick<SystemTaskObservationItem, 'duration_ms' | 'started_at' | 'completed_at'>): string => {
  const directValue = Number(task.duration_ms)
  if (Number.isFinite(directValue) && directValue >= 0) {
    if (directValue < 1000) return `${Math.round(directValue)}ms`
    return `${(directValue / 1000).toFixed(1)}s`
  }

  if (!task.started_at || !task.completed_at) return '-'
  const start = new Date(task.started_at).getTime()
  const end = new Date(task.completed_at).getTime()
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return '-'

  const diff = end - start
  if (diff < 1000) return `${Math.round(diff)}ms`
  return `${(diff / 1000).toFixed(1)}s`
}

const jsonPreview = (payload: unknown): string => {
  if (payload === null || payload === undefined) return '-'
  if (typeof payload === 'string') return payload
  try {
    return JSON.stringify(payload, null, 2)
  } catch {
    return String(payload)
  }
}

const fetchSummary = async () => {
  summary.value = await getSystemTaskSummary()
}

const fetchList = async () => {
  loadingList.value = true
  errorMessage.value = ''
  try {
    const data = await getSystemTasks(buildListParams())
    total.value = Number(data?.count || 0)
    tasks.value = Array.isArray(data?.results) ? data.results : []
    if (page.value > totalPages.value) {
      page.value = totalPages.value
    }
  } catch (error) {
    console.error('Failed to load tasks:', error)
    errorMessage.value = '加载任务列表失败，请稍后重试。'
  } finally {
    loadingList.value = false
  }
}

const fetchSchedulerLogs = async () => {
  schedulerLogsLoading.value = true
  try {
    const data = await getWeeklySchedulerLogs({
      page: schedulerLogsPage.value,
      limit: schedulerLogsLimit.value,
    })
    schedulerLogsTotal.value = Number(data?.count || 0)
    schedulerLogs.value = Array.isArray(data?.results) ? data.results : []
    if (schedulerLogsPage.value > schedulerLogsTotalPages.value) {
      schedulerLogsPage.value = schedulerLogsTotalPages.value
      const fallbackData = await getWeeklySchedulerLogs({
        page: schedulerLogsPage.value,
        limit: schedulerLogsLimit.value,
      })
      schedulerLogsTotal.value = Number(fallbackData?.count || 0)
      schedulerLogs.value = Array.isArray(fallbackData?.results) ? fallbackData.results : []
    }
  } catch (error) {
    console.error('Failed to load weekly scheduler logs:', error)
    schedulerLogsTotal.value = 0
    schedulerLogs.value = []
  } finally {
    schedulerLogsLoading.value = false
  }
}

const refreshAll = async () => {
  try {
    await Promise.all([fetchSummary(), fetchList(), fetchSchedulerLogs()])
  } catch (error) {
    console.error('Failed to refresh task queue:', error)
  }
}

const refreshDetailEvents = async () => {
  if (!detailTask.value?.task_id) return
  try {
    const eventsPayload = await getSystemTaskEvents(detailTask.value.task_id, { limit: 200 })
    detailEvents.value = normalizeEvents(eventsPayload)
  } catch (error) {
    console.error('Failed to load task events:', error)
  }
}

const openTaskDetail = async (taskId: string) => {
  loadingDetail.value = true
  detailVisible.value = true
  try {
    const [detail, eventsPayload] = await Promise.all([
      getSystemTaskDetail(taskId),
      getSystemTaskEvents(taskId, { limit: 200 }),
    ])
    detailTask.value = detail
    detailEvents.value = normalizeEvents(eventsPayload)
    if (!detailEvents.value.length && Array.isArray(detail?.events)) {
      detailEvents.value = detail.events
    }
  } catch (error) {
    console.error('Failed to load task detail:', error)
    detailTask.value = null
    detailEvents.value = []
  } finally {
    loadingDetail.value = false
  }
}

const applyFilters = async () => {
  page.value = 1
  await fetchList()
}

const resetFilters = async () => {
  filters.status = ''
  filters.taskType = ''
  filters.taskId = ''
  filters.runId = ''
  filters.createdRange = null
  await applyFilters()
}

const handleRefresh = async () => {
  await refreshAll()
  if (detailVisible.value && detailTask.value?.task_id) {
    await openTaskDetail(detailTask.value.task_id)
  }
}

const goPrevPage = async () => {
  if (page.value <= 1) return
  page.value -= 1
  await fetchList()
}

const goNextPage = async () => {
  if (page.value >= totalPages.value) return
  page.value += 1
  await fetchList()
}

const goPrevSchedulerLogsPage = async () => {
  if (schedulerLogsPage.value <= 1) return
  schedulerLogsPage.value -= 1
  await fetchSchedulerLogs()
}

const goNextSchedulerLogsPage = async () => {
  if (schedulerLogsPage.value >= schedulerLogsTotalPages.value) return
  schedulerLogsPage.value += 1
  await fetchSchedulerLogs()
}

const filterByRunId = async (runIdRaw: string | null | undefined) => {
  const runId = String(runIdRaw || '').trim()
  if (!runId) return
  filters.runId = runId
  page.value = 1
  await fetchList()
}

const stopAutoRefreshTimer = () => {
  if (autoRefreshTimer !== null) {
    window.clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const startAutoRefreshTimer = () => {
  stopAutoRefreshTimer()
  autoRefreshTimer = window.setInterval(() => {
    void refreshAll()
  }, 10_000)
}

const applyTaskIdFromRoute = async (taskIdRaw: unknown) => {
  const taskId = typeof taskIdRaw === 'string' ? taskIdRaw.trim() : ''
  if (!taskId) return
  filters.taskId = taskId
  await applyFilters()
}

const applyRunIdFromRoute = async (runIdRaw: unknown) => {
  const runId = typeof runIdRaw === 'string' ? runIdRaw.trim() : ''
  if (!runId) return
  filters.runId = runId
  await applyFilters()
}

watch(autoRefresh, (enabled) => {
  if (enabled) {
    startAutoRefreshTimer()
  } else {
    stopAutoRefreshTimer()
  }
}, { immediate: true })

watch(() => route.query.task_id, (value) => {
  void applyTaskIdFromRoute(value)
})

watch(() => route.query.run_id, (value) => {
  void applyRunIdFromRoute(value)
})

onMounted(async () => {
  await refreshAll()
  await applyTaskIdFromRoute(route.query.task_id)
  await applyRunIdFromRoute(route.query.run_id)
})

onBeforeUnmount(() => {
  stopAutoRefreshTimer()
})
</script>
