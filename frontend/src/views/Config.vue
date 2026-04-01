<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-100">配置管理</h2>

    <div
      v-if="message"
      class="flex items-center justify-between rounded-xl border px-3 py-2"
      :class="messageType === 'success'
        ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-500/35 dark:bg-green-500/12 dark:text-green-300'
        : 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/35 dark:bg-red-500/12 dark:text-red-300'"
    >
      <div class="flex items-center gap-2">
        <span>{{ message }}</span>
        <Button
          v-if="(lastTriggeredTaskId || lastTriggeredRunId) && messageType === 'success'"
          size="small"
          text
          class="!px-2 !py-1 !text-current underline"
          @click="goToTaskQueue(lastTriggeredTaskId, lastTriggeredRunId)"
        >
          查看任务队列
        </Button>
      </div>
      <IconButton
        size="small"
        class="!h-6 !w-6 !text-current/70"
        aria-label="关闭提示"
        @click="clearMessage"
      >
        ×
      </IconButton>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab
          v-for="tab in tabs"
          :key="tab.key"
          :value="tab.key"
        >
          {{ tab.label }}
        </Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="gitlab">
          <GitLabConfigTab
            v-model:config="config.gitlab"
            :saving="saving"
            @save="handleGitLabSave"
            @reset="handleGitLabReset"
          />
        </TabPanel>

        <TabPanel value="llm-providers">
          <LLMProviderTab />
        </TabPanel>

        <TabPanel value="review-snippet">
          <ReviewSnippetConfigTab
            v-model:source="config.system.reviewCodeSnippetSource"
            :saving="savingSystemConfig"
            :dirty="isSystemConfigDirty"
            @save="handleSystemConfigSave"
            @reset="handleSystemConfigReset"
          />
        </TabPanel>

        <TabPanel value="weekly-snapshot">
          <WeeklySnapshotSchedulerConfigTab
            v-model:config="config.system.weeklySnapshotScheduler"
            :saving="savingWeeklySnapshotConfig"
            :dirty="isWeeklySnapshotConfigDirty"
            :triggering="triggeringWeeklySnapshot"
            @save="handleWeeklySnapshotConfigSave"
            @reset="handleWeeklySnapshotConfigReset"
            @generate-now="handleGenerateWeeklySnapshotNow"
          />
        </TabPanel>

        <TabPanel value="maintenance">
          <MaintenanceOperationsTab />
        </TabPanel>

        <TabPanel value="webhook-events">
          <WebhookEventRulesTab
            :rules="webhookEventRules"
            @refresh-rules="refreshWebhookEventRules"
          />
        </TabPanel>

        <TabPanel value="notification">
          <NotificationChannelsTab
            :channels="channels"
            @refresh-channels="refreshChannels"
          />
        </TabPanel>

        <TabPanel value="auth-users">
          <AuthUsersTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getConfigSummary,
  batchUpdateConfig,
  getSystemConfigs,
  updateSystemConfigs,
  getNotificationChannels,
  getWebhookEventRules,
  triggerDeveloperWeeklyLastWeekSummary
} from '@/api/index'
import GitLabConfigTab from '@/components/config/GitLabConfigTab.vue'
import LLMProviderTab from '@/components/config/LLMProviderTab.vue'
import WebhookEventRulesTab from '@/components/config/WebhookEventRulesTab.vue'
import NotificationChannelsTab from '@/components/config/NotificationChannelsTab.vue'
import AuthUsersTab from '@/components/config/AuthUsersTab.vue'
import ReviewSnippetConfigTab from '@/components/config/ReviewSnippetConfigTab.vue'
import WeeklySnapshotSchedulerConfigTab, {
  type WeeklySnapshotSchedulerForm,
  type WeeklySummaryStatus
} from '@/components/config/WeeklySnapshotSchedulerConfigTab.vue'
import MaintenanceOperationsTab from '@/components/config/MaintenanceOperationsTab.vue'
import IconButton from '@/components/ui/IconButton.vue'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

const activeTab = ref('gitlab')
const router = useRouter()
const tabs = [
  { key: 'gitlab', label: 'GitLab 配置' },
  { key: 'llm-providers', label: 'LLM 供应商' },
  { key: 'review-snippet', label: '问题代码' },
  { key: 'weekly-snapshot', label: '周报调度' },
  { key: 'maintenance', label: '运维' },
  { key: 'webhook-events', label: 'Webhook 事件' },
  { key: 'notification', label: '通知配置' },
  { key: 'auth-users', label: '账号管理' },
]
const saving = ref(false)
const savingSystemConfig = ref(false)
const savingWeeklySnapshotConfig = ref(false)
const triggeringWeeklySnapshot = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const lastTriggeredTaskId = ref('')
const lastTriggeredRunId = ref('')
let messageTimer: number | null = null

const defaultWeeklySnapshotSchedulerConfig = (): WeeklySnapshotSchedulerForm => ({
  enabled: false,
  triggerWeekday: 0,
  triggerHour: 1,
  pollSeconds: 300,
  useLlm: true,
  autoIgnoreStrategyEnabled: false,
  autoIgnoreStrategyApply: true,
  includeStatuses: ['open', 'reopened'],
})

const config = ref({
  llm: { provider: 'openai', model: 'gpt-4', apiKey: '', apiBase: '' },
  gitlab: { serverUrl: 'https://gitlab.com', privateToken: '', siteUrl: '' },
  system: {
    reviewCodeSnippetSource: 'line' as 'line' | 'llm',
    weeklySnapshotScheduler: defaultWeeklySnapshotSchedulerConfig(),
  },
})

const channels = ref<any[]>([])
const webhookEventRules = ref<any[]>([])
const originalConfig = ref({})

const normalizeReviewCodeSnippetSource = (value: unknown): 'line' | 'llm' => {
  const normalized = String(value || '').trim().toLowerCase()
  return normalized === 'llm' ? 'llm' : 'line'
}

const parseBooleanConfigValue = (value: unknown, fallback: boolean): boolean => {
  const normalized = String(value ?? '').trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return fallback
}

const parseIntConfigValue = (value: unknown, fallback: number, min: number, max: number): number => {
  const parsed = Number.parseInt(String(value ?? '').trim(), 10)
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(max, Math.max(min, parsed))
}

const normalizeWeeklySummaryStatuses = (value: unknown): WeeklySummaryStatus[] => {
  const items = Array.isArray(value) ? value : []
  const set = new Set<WeeklySummaryStatus>()
  for (const item of items) {
    const raw = String(item || '').trim().toLowerCase()
    if (raw === 'open' || raw === 'ignored' || raw === 'reopened') {
      set.add(raw)
    }
  }
  const ordered = (['open', 'ignored', 'reopened'] as WeeklySummaryStatus[]).filter((item) => set.has(item))
  return ordered.length ? ordered : ['open', 'reopened']
}

const parseStatusConfigValue = (value: unknown): WeeklySummaryStatus[] => {
  const text = String(value ?? '').trim()
  if (!text) return ['open', 'reopened']
  try {
    const parsed = JSON.parse(text)
    return normalizeWeeklySummaryStatuses(parsed)
  } catch {
    return normalizeWeeklySummaryStatuses(text.split(','))
  }
}

const isSystemConfigDirty = computed(() => {
  const original = JSON.parse(JSON.stringify(originalConfig.value || {}))
  const originalSource = normalizeReviewCodeSnippetSource(original?.system?.reviewCodeSnippetSource)
  return config.value.system.reviewCodeSnippetSource !== originalSource
})

const normalizeWeeklySnapshotScheduler = (value: unknown): WeeklySnapshotSchedulerForm => {
  const raw = (value ?? {}) as Partial<WeeklySnapshotSchedulerForm>
  return {
    enabled: Boolean(raw.enabled),
    triggerWeekday: parseIntConfigValue(raw.triggerWeekday, 0, 0, 6),
    triggerHour: parseIntConfigValue(raw.triggerHour, 1, 0, 23),
    pollSeconds: parseIntConfigValue(raw.pollSeconds, 300, 5, 3600),
    useLlm: raw.useLlm === undefined ? true : Boolean(raw.useLlm),
    autoIgnoreStrategyEnabled: raw.autoIgnoreStrategyEnabled === undefined ? false : Boolean(raw.autoIgnoreStrategyEnabled),
    autoIgnoreStrategyApply: raw.autoIgnoreStrategyApply === undefined ? true : Boolean(raw.autoIgnoreStrategyApply),
    includeStatuses: normalizeWeeklySummaryStatuses(raw.includeStatuses),
  }
}

const isWeeklySnapshotConfigDirty = computed(() => {
  const original = JSON.parse(JSON.stringify(originalConfig.value || {}))
  const current = normalizeWeeklySnapshotScheduler(config.value.system.weeklySnapshotScheduler)
  const baseline = normalizeWeeklySnapshotScheduler(original?.system?.weeklySnapshotScheduler)
  return JSON.stringify(current) !== JSON.stringify(baseline)
})

const clearMessage = () => {
  message.value = ''
  lastTriggeredTaskId.value = ''
  lastTriggeredRunId.value = ''
  if (messageTimer !== null) {
    window.clearTimeout(messageTimer)
    messageTimer = null
  }
}

const showMessage = (
  text: string,
  type: 'success' | 'error' = 'success',
  options?: { taskId?: string; runId?: string; durationMs?: number }
) => {
  message.value = text
  messageType.value = type
  lastTriggeredTaskId.value = options?.taskId ? String(options.taskId).trim() : ''
  lastTriggeredRunId.value = options?.runId ? String(options.runId).trim() : ''
  if (messageTimer !== null) {
    window.clearTimeout(messageTimer)
  }
  const durationMs = Math.max(2000, options?.durationMs ?? 3000)
  messageTimer = window.setTimeout(() => {
    clearMessage()
  }, durationMs)
}

const goToTaskQueue = (taskId?: string, runId?: string) => {
  const normalizedTaskId = String(taskId || '').trim()
  const normalizedRunId = String(runId || '').trim()
  const query: Record<string, string> = {}
  if (normalizedTaskId) query.task_id = normalizedTaskId
  if (normalizedRunId) query.run_id = normalizedRunId
  void router.push({
    path: '/task-queue',
    query: Object.keys(query).length ? query : undefined,
  })
  clearMessage()
}

const normalizeChannelList = (data: any) => {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  if (Array.isArray(data.channels)) return data.channels
  return []
}

const refreshChannels = async () => {
  try {
    const response = await getNotificationChannels()
    channels.value = normalizeChannelList(response)
  } catch (error) {
    console.error('Failed to load channels:', error)
    showMessage('加载通知通道失败', 'error')
  }
}

const refreshWebhookEventRules = async () => {
  try {
    const response = await getWebhookEventRules()
    if (response?.results) {
      webhookEventRules.value = response.results
    } else if (Array.isArray(response)) {
      webhookEventRules.value = response
    } else {
      webhookEventRules.value = []
    }
  } catch (error) {
    console.error('Failed to load webhook event rules:', error)
    showMessage('加载webhook事件规则失败', 'error')
  }
}

const loadConfig = async () => {
  try {
    const data = await getConfigSummary()

    if (data.llm) {
      config.value.llm = {
        provider: data.llm.provider || 'openai',
        model: data.llm.model || 'gpt-4',
        apiKey: data.llm.api_key || '',
        apiBase: data.llm.api_base || ''
      }
    }
    if (data.gitlab) {
      config.value.gitlab = {
        serverUrl: data.gitlab.server_url || 'https://gitlab.com',
        privateToken: data.gitlab.private_token || '',
        siteUrl: data.gitlab.site_url || ''
      }
    }

    if (data.channels) {
      channels.value = normalizeChannelList(data.channels)
    } else {
      await refreshChannels()
    }

    if (data.webhook_events) {
      webhookEventRules.value = Array.isArray(data.webhook_events) ? data.webhook_events : []
    } else {
      await refreshWebhookEventRules()
    }

    const systemConfigList = await getSystemConfigs()
    if (Array.isArray(systemConfigList)) {
      const systemConfigMap = new Map<string, string>()
      for (const item of systemConfigList) {
        const key = String(item?.key || '').trim()
        if (!key) continue
        systemConfigMap.set(key, String(item?.value ?? ''))
      }
      const sourceConfig = systemConfigList.find(
        (item: any) => String(item?.key || '') === 'review.code_snippet_source'
      )
      config.value.system.reviewCodeSnippetSource = normalizeReviewCodeSnippetSource(sourceConfig?.value)
      config.value.system.weeklySnapshotScheduler = {
        enabled: parseBooleanConfigValue(
          systemConfigMap.get('reports.developer_weekly.auto_enabled'),
          false
        ),
        triggerWeekday: parseIntConfigValue(
          systemConfigMap.get('reports.developer_weekly.auto_trigger_weekday'),
          0,
          0,
          6
        ),
        triggerHour: parseIntConfigValue(
          systemConfigMap.get('reports.developer_weekly.auto_trigger_hour'),
          1,
          0,
          23
        ),
        pollSeconds: parseIntConfigValue(
          systemConfigMap.get('reports.developer_weekly.auto_poll_seconds'),
          300,
          5,
          3600
        ),
        useLlm: parseBooleanConfigValue(
          systemConfigMap.get('reports.developer_weekly.auto_use_llm'),
          true
        ),
        autoIgnoreStrategyEnabled: parseBooleanConfigValue(
          systemConfigMap.get('reports.ignore_strategy.auto_enabled'),
          false
        ),
        autoIgnoreStrategyApply: parseBooleanConfigValue(
          systemConfigMap.get('reports.ignore_strategy.auto_apply'),
          true
        ),
        includeStatuses: parseStatusConfigValue(
          systemConfigMap.get('reports.developer_weekly.include_statuses')
        ),
      }
    }

    originalConfig.value = JSON.parse(JSON.stringify(config.value))
  } catch (error) {
    console.error('Failed to load config:', error)
    showMessage('加载配置失败', 'error')
  }
}

const handleGitLabSave = async () => {
  saving.value = true
  try {
    const apiData = {
      gitlab: {
        server_url: config.value.gitlab.serverUrl,
        private_token: config.value.gitlab.privateToken,
        site_url: config.value.gitlab.siteUrl,
        is_active: true
      }
    }
    await batchUpdateConfig(apiData)
    showMessage('配置保存成功')
    originalConfig.value = JSON.parse(JSON.stringify(config.value))
  } catch (error) {
    console.error('Failed to save config:', error)
    showMessage('保存配置失败', 'error')
  } finally {
    saving.value = false
  }
}

const handleGitLabReset = () => {
  if (!JSON.stringify(originalConfig.value)) return
  const original = JSON.parse(JSON.stringify(originalConfig.value))
  if (original?.gitlab) {
    config.value.gitlab = original.gitlab
    showMessage('GitLab 配置已重置')
  }
}

const handleSystemConfigSave = async () => {
  savingSystemConfig.value = true
  try {
    await updateSystemConfigs({
      configs: {
        'review.code_snippet_source': config.value.system.reviewCodeSnippetSource,
      },
    })
    showMessage('问题代码配置保存成功')
    originalConfig.value = JSON.parse(JSON.stringify(config.value))
  } catch (error) {
    console.error('Failed to save system config:', error)
    showMessage('保存问题代码配置失败', 'error')
  } finally {
    savingSystemConfig.value = false
  }
}

const handleSystemConfigReset = () => {
  if (!JSON.stringify(originalConfig.value)) return
  const original = JSON.parse(JSON.stringify(originalConfig.value))
  config.value.system.reviewCodeSnippetSource = normalizeReviewCodeSnippetSource(
    original?.system?.reviewCodeSnippetSource
  )
  showMessage('问题代码配置已重置')
}

const handleWeeklySnapshotConfigSave = async () => {
  savingWeeklySnapshotConfig.value = true
  try {
    const schedulerConfig = normalizeWeeklySnapshotScheduler(config.value.system.weeklySnapshotScheduler)
    await updateSystemConfigs({
      configs: {
        'reports.developer_weekly.auto_enabled': String(schedulerConfig.enabled),
        'reports.developer_weekly.auto_trigger_weekday': String(schedulerConfig.triggerWeekday),
        'reports.developer_weekly.auto_trigger_hour': String(schedulerConfig.triggerHour),
        'reports.developer_weekly.auto_poll_seconds': String(schedulerConfig.pollSeconds),
        'reports.developer_weekly.auto_use_llm': String(schedulerConfig.useLlm),
        'reports.ignore_strategy.auto_enabled': String(schedulerConfig.autoIgnoreStrategyEnabled),
        'reports.ignore_strategy.auto_apply': String(schedulerConfig.autoIgnoreStrategyApply),
        'reports.developer_weekly.include_statuses': JSON.stringify(schedulerConfig.includeStatuses),
      },
    })
    showMessage('周报调度配置保存成功')
    originalConfig.value = JSON.parse(JSON.stringify(config.value))
  } catch (error) {
    console.error('Failed to save weekly snapshot scheduler config:', error)
    showMessage('保存周报调度配置失败', 'error')
  } finally {
    savingWeeklySnapshotConfig.value = false
  }
}

const handleWeeklySnapshotConfigReset = () => {
  if (!JSON.stringify(originalConfig.value)) return
  const original = JSON.parse(JSON.stringify(originalConfig.value))
  config.value.system.weeklySnapshotScheduler = normalizeWeeklySnapshotScheduler(
    original?.system?.weeklySnapshotScheduler
  )
  showMessage('周报调度配置已重置')
}

const handleGenerateWeeklySnapshotNow = async () => {
  triggeringWeeklySnapshot.value = true
  try {
    const schedulerConfig = normalizeWeeklySnapshotScheduler(config.value.system.weeklySnapshotScheduler)
    const response = await triggerDeveloperWeeklyLastWeekSummary({
      include_statuses: schedulerConfig.includeStatuses,
      use_llm: schedulerConfig.useLlm,
    })
    const taskId = String(response?.task_id || '').trim()
    const runId = String(response?.run_id || '').trim()
    if (taskId) {
      showMessage(`已触发上周周报生成任务：${taskId}${runId ? `（run: ${runId}）` : ''}`, 'success', {
        taskId,
        runId,
        durationMs: 12000,
      })
    } else {
      showMessage('已触发上周周报生成任务')
    }
  } catch (error) {
    console.error('Failed to trigger weekly snapshot generation:', error)
    showMessage('触发上周周报生成失败', 'error')
  } finally {
    triggeringWeeklySnapshot.value = false
  }
}

onMounted(() => loadConfig())
onBeforeUnmount(() => clearMessage())
</script>
