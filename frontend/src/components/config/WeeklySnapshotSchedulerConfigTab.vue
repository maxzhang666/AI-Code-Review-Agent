<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="成员周报调度" dot-class="bg-violet-500" />

        <div class="rounded-xl border border-violet-200/60 bg-gradient-to-r from-violet-50 to-indigo-50 p-4 text-violet-700 dark:border-violet-500/35 dark:from-violet-500/12 dark:to-indigo-500/12 dark:text-violet-200">
          <div class="mb-2 flex items-center gap-2 font-medium">
            <CalendarClock class="h-4 w-4" />
            自动化生成说明
          </div>
          <div class="space-y-1 text-xs text-violet-700/90 dark:text-violet-100/90">
            <div>1. 自动调度会在指定时间触发“上周成员周总结”生成任务。</div>
            <div>2. 同一统计周仅会自动入队一次，避免重复生成。</div>
            <div>3. 开启 LLM 后将优先用模型提炼，总结失败会自动回退为规则文案。</div>
          </div>
        </div>

        <div class="space-y-3">
          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-surface-900 dark:text-surface-0">启用自动生成</div>
                <div class="mt-1 text-xs text-surface-600 dark:text-surface-300">关闭时仅支持手动触发。</div>
              </div>
              <ToggleSwitch
                :model-value="config.enabled"
                @update:model-value="updateConfig({ enabled: Boolean($event) })"
              />
            </div>
          </div>

          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="mb-2 text-sm font-semibold text-surface-900 dark:text-surface-0">触发星期</div>
            <SelectButton
              :model-value="config.triggerWeekday"
              :options="weekdayOptions"
              option-label="label"
              option-value="value"
              size="small"
              @update:model-value="updateConfig({ triggerWeekday: normalizeWeekday($event) })"
            />
          </div>

          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
              <label class="mb-2 block text-sm font-semibold text-surface-900 dark:text-surface-0">触发小时</label>
              <input
                :value="config.triggerHour"
                type="number"
                min="0"
                max="23"
                class="h-10 w-full rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-100"
                @input="onTriggerHourInput"
              >
              <div class="mt-1 text-xs text-surface-500">范围 0-23，按配置时区执行。</div>
            </div>

            <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
              <label class="mb-2 block text-sm font-semibold text-surface-900 dark:text-surface-0">轮询间隔（秒）</label>
              <input
                :value="config.pollSeconds"
                type="number"
                min="5"
                max="3600"
                class="h-10 w-full rounded-md border border-surface-300 bg-surface-0 px-3 text-sm text-surface-700 outline-none transition-colors focus:border-primary-400 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-100"
                @input="onPollSecondsInput"
              >
              <div class="mt-1 text-xs text-surface-500">范围 5-3600 秒，建议 60-300。</div>
            </div>
          </div>

          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-surface-900 dark:text-surface-0">使用 LLM 提炼总结</div>
                <div class="mt-1 text-xs text-surface-600 dark:text-surface-300">关闭后只使用规则文案，生成速度更稳定。</div>
              </div>
              <ToggleSwitch
                :model-value="config.useLlm"
                @update:model-value="updateConfig({ useLlm: Boolean($event) })"
              />
            </div>
          </div>

          <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 p-3 dark:border-surface-700/70 dark:bg-surface-900">
            <div class="mb-2 text-sm font-semibold text-surface-900 dark:text-surface-0">总结纳入状态</div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="option in statusOptions"
                :key="option.value"
                type="button"
                class="rounded-md border px-3 py-1.5 text-xs transition-colors"
                :class="config.includeStatuses.includes(option.value)
                  ? 'border-primary-400 bg-primary-50 text-primary-700 dark:border-primary-500/70 dark:bg-primary-500/15 dark:text-primary-200'
                  : 'border-surface-300 bg-surface-0 text-surface-600 hover:border-surface-400 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-300 dark:hover:border-surface-600'"
                @click="toggleStatus(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <div class="mt-2 text-xs text-surface-500">默认排除 ignored，至少保留一个状态。</div>
          </div>

          <div class="rounded-lg border border-emerald-200/70 bg-emerald-50/70 p-3 dark:border-emerald-500/35 dark:bg-emerald-500/10">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-emerald-800 dark:text-emerald-200">手动生成</div>
                <div class="mt-1 text-xs text-emerald-700/90 dark:text-emerald-100/90">立即触发一次“上周成员周报”生成任务（异步入队）。</div>
              </div>
              <Button
                label="立即生成上周周报"
                size="small"
                :loading="triggering"
                @click="emit('generate-now')"
              />
            </div>
          </div>
        </div>

        <ConfigActionBar
          :saving="saving"
          :save-disabled="!dirty"
          @reset="emit('reset')"
          @save="emit('save')"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { CalendarClock } from 'lucide-vue-next'
import ConfigSectionHeader from '@/components/config/ConfigSectionHeader.vue'
import ConfigActionBar from '@/components/config/ConfigActionBar.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'

export type WeeklySummaryStatus = 'open' | 'ignored' | 'reopened'

export interface WeeklySnapshotSchedulerForm {
  enabled: boolean
  triggerWeekday: number
  triggerHour: number
  pollSeconds: number
  useLlm: boolean
  includeStatuses: WeeklySummaryStatus[]
}

const props = withDefaults(
  defineProps<{
    config: WeeklySnapshotSchedulerForm
    saving?: boolean
    dirty?: boolean
    triggering?: boolean
  }>(),
  {
    saving: false,
    dirty: false,
    triggering: false,
  }
)

const emit = defineEmits<{
  'update:config': [value: WeeklySnapshotSchedulerForm]
  save: []
  reset: []
  'generate-now': []
}>()

const weekdayOptions = [
  { label: '周一', value: 0 },
  { label: '周二', value: 1 },
  { label: '周三', value: 2 },
  { label: '周四', value: 3 },
  { label: '周五', value: 4 },
  { label: '周六', value: 5 },
  { label: '周日', value: 6 },
]

const statusOptions: Array<{ label: string; value: WeeklySummaryStatus }> = [
  { label: 'open', value: 'open' },
  { label: 'reopened', value: 'reopened' },
  { label: 'ignored', value: 'ignored' },
]

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const normalizeWeekday = (value: unknown): number => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 0
  return clamp(Math.round(parsed), 0, 6)
}

const normalizeTriggerHour = (value: unknown): number => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 1
  return clamp(Math.round(parsed), 0, 23)
}

const normalizePollSeconds = (value: unknown): number => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 300
  return clamp(Math.round(parsed), 5, 3600)
}

const updateConfig = (patch: Partial<WeeklySnapshotSchedulerForm>) => {
  emit('update:config', {
    ...props.config,
    ...patch,
  })
}

const statusOrder: WeeklySummaryStatus[] = ['open', 'ignored', 'reopened']

const normalizeStatuses = (value: unknown): WeeklySummaryStatus[] => {
  const list = Array.isArray(value) ? value : []
  const set = new Set<WeeklySummaryStatus>()
  for (const item of list) {
    const text = String(item || '').trim().toLowerCase()
    if (text === 'open' || text === 'ignored' || text === 'reopened') {
      set.add(text)
    }
  }
  const normalized = statusOrder.filter((item) => set.has(item))
  return normalized.length ? normalized : ['open', 'reopened']
}

const toggleStatus = (status: WeeklySummaryStatus) => {
  const current = normalizeStatuses(props.config.includeStatuses)
  const set = new Set<WeeklySummaryStatus>(current)
  if (set.has(status)) {
    if (set.size <= 1) return
    set.delete(status)
  } else {
    set.add(status)
  }
  const next = statusOrder.filter((item) => set.has(item))
  updateConfig({ includeStatuses: next })
}

const onTriggerHourInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  updateConfig({ triggerHour: normalizeTriggerHour(target.value) })
}

const onPollSecondsInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  updateConfig({ pollSeconds: normalizePollSeconds(target.value) })
}
</script>
