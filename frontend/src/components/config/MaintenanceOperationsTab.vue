<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="运维菜单" dot-class="bg-amber-500" />

        <div class="rounded-xl border border-amber-200/60 bg-gradient-to-r from-amber-50 to-orange-50 p-4 text-amber-800 dark:border-amber-500/35 dark:from-amber-500/12 dark:to-orange-500/12 dark:text-amber-100">
          <div class="text-sm font-semibold">内置清理能力</div>
          <div class="mt-1 text-xs leading-5 text-amber-800/90 dark:text-amber-100/90">
            清理任务事件与周报调度日志，支持先预估再执行，避免依赖服务器脚本。
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-4 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="text-sm font-semibold text-surface-900 dark:text-surface-0">任务事件清理</div>
            <div class="mt-1 text-xs text-surface-600 dark:text-surface-300">资源：`task_events`</div>

            <label class="mt-3 block text-xs text-surface-600 dark:text-surface-300">保留天数</label>
            <input
              v-model.number="taskEventsRetentionDays"
              type="number"
              min="1"
              max="3650"
              class="mt-1 h-10 w-full rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-100"
            >

            <div class="mt-3 flex flex-wrap gap-2">
              <Button label="预估清理" size="small" outlined :loading="taskEventsLoadingPreview" @click="previewTaskEvents" />
              <Button label="立即清理" size="small" severity="warn" :loading="taskEventsLoadingExecute" @click="executeTaskEvents" />
            </div>

            <pre class="mt-3 max-h-[220px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ taskEventsResultText }}</pre>
          </div>

          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-4 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="text-sm font-semibold text-surface-900 dark:text-surface-0">周报调度日志清理</div>
            <div class="mt-1 text-xs text-surface-600 dark:text-surface-300">资源：`weekly_snapshot_scheduler_logs`</div>

            <label class="mt-3 block text-xs text-surface-600 dark:text-surface-300">保留天数</label>
            <input
              v-model.number="schedulerLogsRetentionDays"
              type="number"
              min="1"
              max="3650"
              class="mt-1 h-10 w-full rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-100"
            >

            <div class="mt-3 flex flex-wrap gap-2">
              <Button label="预估清理" size="small" outlined :loading="schedulerLogsLoadingPreview" @click="previewSchedulerLogs" />
              <Button label="立即清理" size="small" severity="warn" :loading="schedulerLogsLoadingExecute" @click="executeSchedulerLogs" />
            </div>

            <pre class="mt-3 max-h-[220px] overflow-auto whitespace-pre-wrap break-all rounded bg-surface-900 p-2 text-xs text-surface-50">{{ schedulerLogsResultText }}</pre>
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  cleanupTaskEventsMaintenance,
  cleanupWeeklySchedulerLogsMaintenance,
  type MaintenanceCleanupResponse,
} from '@/api'
import ConfigSectionHeader from '@/components/config/ConfigSectionHeader.vue'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'

const taskEventsRetentionDays = ref(30)
const schedulerLogsRetentionDays = ref(90)

const taskEventsLoadingPreview = ref(false)
const taskEventsLoadingExecute = ref(false)
const schedulerLogsLoadingPreview = ref(false)
const schedulerLogsLoadingExecute = ref(false)

const taskEventsResultText = ref('尚未执行')
const schedulerLogsResultText = ref('尚未执行')

const normalizeRetentionDays = (value: unknown, fallback: number): number => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  const normalized = Math.round(num)
  return Math.min(3650, Math.max(1, normalized))
}

const formatResult = (result: MaintenanceCleanupResponse): string => {
  return JSON.stringify(result, null, 2)
}

const runTaskEvents = async (dryRun: boolean) => {
  const retentionDays = normalizeRetentionDays(taskEventsRetentionDays.value, 30)
  taskEventsRetentionDays.value = retentionDays
  const response = await cleanupTaskEventsMaintenance({
    retention_days: retentionDays,
    dry_run: dryRun,
  })
  taskEventsResultText.value = formatResult(response)
  if (!dryRun) {
    toast.success(`任务事件清理完成，删除 ${response.deleted_count} 条`) 
  }
}

const runSchedulerLogs = async (dryRun: boolean) => {
  const retentionDays = normalizeRetentionDays(schedulerLogsRetentionDays.value, 90)
  schedulerLogsRetentionDays.value = retentionDays
  const response = await cleanupWeeklySchedulerLogsMaintenance({
    retention_days: retentionDays,
    dry_run: dryRun,
  })
  schedulerLogsResultText.value = formatResult(response)
  if (!dryRun) {
    toast.success(`调度日志清理完成，删除 ${response.deleted_count} 条`)
  }
}

const previewTaskEvents = async () => {
  taskEventsLoadingPreview.value = true
  try {
    await runTaskEvents(true)
  } catch (error) {
    console.error('Failed to preview task_events cleanup:', error)
    toast.error('预估任务事件清理失败')
  } finally {
    taskEventsLoadingPreview.value = false
  }
}

const executeTaskEvents = async () => {
  const confirmed = window.confirm('确认执行任务事件清理？该操作会删除过期数据。')
  if (!confirmed) return

  taskEventsLoadingExecute.value = true
  try {
    await runTaskEvents(false)
  } catch (error) {
    console.error('Failed to execute task_events cleanup:', error)
    toast.error('执行任务事件清理失败')
  } finally {
    taskEventsLoadingExecute.value = false
  }
}

const previewSchedulerLogs = async () => {
  schedulerLogsLoadingPreview.value = true
  try {
    await runSchedulerLogs(true)
  } catch (error) {
    console.error('Failed to preview weekly scheduler logs cleanup:', error)
    toast.error('预估周报调度日志清理失败')
  } finally {
    schedulerLogsLoadingPreview.value = false
  }
}

const executeSchedulerLogs = async () => {
  const confirmed = window.confirm('确认执行周报调度日志清理？该操作会删除过期数据。')
  if (!confirmed) return

  schedulerLogsLoadingExecute.value = true
  try {
    await runSchedulerLogs(false)
  } catch (error) {
    console.error('Failed to execute weekly scheduler logs cleanup:', error)
    toast.error('执行周报调度日志清理失败')
  } finally {
    schedulerLogsLoadingExecute.value = false
  }
}
</script>
