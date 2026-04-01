<template>
  <div class="space-y-6">
    <div class="flex items-center gap-4">
      <Button text rounded label="返回" @click="goBack">
        <template #icon><ArrowLeft class="w-4 h-4" /></template>
      </Button>
      <div class="flex-1">
        <h1 class="text-xl font-semibold tracking-tight text-color">{{ project?.project_name }}</h1>
        <p class="text-xs text-surface-500 mt-1">{{ project?.namespace }}</p>
      </div>
      <Tag :severity="isReviewEnabled(project?.review_enabled) ? 'success' : 'secondary'">
        {{ isReviewEnabled(project?.review_enabled) ? '审查已开启' : '审查已关闭' }}
      </Tag>
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

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div class="lg:col-span-3">
          <TabPanels>
            <TabPanel value="info">
              <ProjectInfoTab :project="project" />
            </TabPanel>

            <TabPanel value="webhook-events">
              <WebhookEventTab
                :project-id="projectId"
                :project="project"
                :webhook-event-rules="webhookEventRules"
                :selected-event-ids="selectedEventIds"
                :llm-providers="llmProviders"
                @update:selected-event-ids="selectedEventIds = $event"
                @saved="onWebhookEventsSaved"
                @provider-saved="loadProjectDetail"
              />
            </TabPanel>

            <TabPanel value="event-prompts">
              <EventPromptTab
                :project-id="projectId"
                :prompts="eventPrompts"
                @saved="loadProjectWebhookEventPrompts"
              />
            </TabPanel>

            <TabPanel value="ignore-strategies">
              <div class="space-y-4">
                <div class="flex flex-col gap-3">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <label class="flex flex-col gap-1 text-xs text-surface-500">
                        <span>状态筛选</span>
                        <Select
                          v-model="selectedIgnoreStrategyStatus"
                          :options="ignoreStrategyStatusOptions"
                          option-label="label"
                          option-value="value"
                          class="w-40"
                          @change="loadProjectIgnoreStrategies"
                        />
                      </label>
                      <label class="flex flex-col gap-1 text-xs text-surface-500">
                        <span>禁用原因（可选）</span>
                        <InputText
                          v-model="ignoreStrategyDisableReason"
                          class="w-full sm:w-72"
                          placeholder="例如：本周策略回收"
                          maxlength="200"
                        />
                      </label>
                    </div>
                    <div class="text-xs text-surface-500">
                      当前共 {{ ignoreStrategies.length }} 条策略
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <Button
                      outlined
                      rounded
                      size="small"
                      label="刷新策略"
                      :disabled="ignoreStrategiesLoading"
                      @click="loadProjectIgnoreStrategies"
                    />
                    <Button
                      severity="danger"
                      rounded
                      size="small"
                      label="全部禁用"
                      :disabled="ignoreStrategiesLoading || !hasEnabledIgnoreStrategies"
                      @click="disableAllIgnoreStrategies"
                    />
                  </div>
                </div>

                <div v-if="ignoreStrategiesLoading" class="rounded-xl border border-surface-200 bg-surface-50 p-6 text-center text-sm text-surface-500">
                  正在加载忽略策略...
                </div>

                <div v-else-if="!ignoreStrategies.length" class="rounded-xl border border-dashed border-surface-300 bg-surface-50 p-6 text-center text-sm text-surface-500">
                  当前仓库暂无可管理的忽略策略
                </div>

                <div v-else class="overflow-x-auto rounded-xl border border-surface-200">
                  <table class="min-w-full divide-y divide-surface-200 text-xs">
                    <thead class="bg-surface-50">
                      <tr>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">规则范围</th>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">状态</th>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">置信度</th>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">样本/周数</th>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">过期时间</th>
                        <th class="px-3 py-2 text-left font-medium text-surface-600">禁用原因</th>
                        <th class="px-3 py-2 text-right font-medium text-surface-600">操作</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-surface-100 bg-white">
                      <tr v-for="item in ignoreStrategies" :key="item.id">
                        <td class="px-3 py-2 align-top">
                          <div class="font-medium text-surface-900">{{ item.rule_key || '-' }}</div>
                          <div class="mt-1 text-surface-500">{{ item.path_pattern || '仓库级（无路径限制）' }}</div>
                        </td>
                        <td class="px-3 py-2 align-top">
                          <Tag :severity="ignoreStrategyStatusSeverity(item.status)" :value="ignoreStrategyStatusLabel(item.status)" />
                        </td>
                        <td class="px-3 py-2 align-top">{{ Number(item.confidence_score || 0).toFixed(2) }}</td>
                        <td class="px-3 py-2 align-top">{{ item.sample_count_4w || 0 }} / {{ item.active_weeks_4w || 0 }}</td>
                        <td class="px-3 py-2 align-top">{{ formatBackendDate(item.expire_at) || '-' }}</td>
                        <td class="px-3 py-2 align-top max-w-[18rem]">
                          <span class="line-clamp-2">{{ item.disabled_reason || '-' }}</span>
                        </td>
                        <td class="px-3 py-2 align-top text-right">
                          <Button
                            text
                            size="small"
                            label="禁用"
                            :disabled="ignoreStrategiesLoading || item.status === 'disabled'"
                            @click="disableIgnoreStrategy(item)"
                          />
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </TabPanel>

            <TabPanel value="notifications">
              <NotificationTab
                :project-id="projectId"
                :channels="notificationChannels"
                :selected-channel-ids="selectedChannelIds"
                :gitlab-comment-enabled="gitlabCommentEnabled"
                @update:selected-channel-ids="selectedChannelIds = $event"
                @update:gitlab-comment-enabled="gitlabCommentEnabled = $event"
                @saved="loadProjectNotificationSettings"
              />
            </TabPanel>

            <TabPanel value="events">
              <RecentEventsTab
                :events="recentEvents"
                :current-page="currentPage"
                :total-events="totalEvents"
                :page-size="pageSize"
                :project-url="project?.project_url"
                @page-change="handlePageChange"
              />
            </TabPanel>
          </TabPanels>
        </div>

        <!-- Right Sidebar -->
        <ProjectSidebar
          class="lg:pt-4"
          :project="project"
          :stats="projectStats"
          :contributors="topContributors"
          :loading="loading"
          @toggle-review="toggleReview"
          @toggle-ignore-strategy="toggleIgnoreStrategy"
          @refresh="refreshData"
        />
      </div>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import {
  getProjectDetail,
  getProjectWebhookLogs,
  getProjectReviewHistory,
  getProjectStatsDetail,
  enableProjectReview,
  disableProjectReview,
  updateProject,
  getNotificationChannels,
  getProjectNotifications,
  getWebhookEventRules,
  getProjectWebhookEvents,
  getProjectWebhookEventPrompts,
  getLLMProviders,
  getProjectIgnoreStrategies,
  disableProjectIgnoreStrategy,
  disableAllProjectIgnoreStrategies,
} from '@/api'
import { toast } from '@/utils/toast'
import { formatBackendDate, parseBackendDate } from '@/utils/datetime'
import ProjectInfoTab from '@/components/project/ProjectInfoTab.vue'
import WebhookEventTab from '@/components/project/WebhookEventTab.vue'
import EventPromptTab from '@/components/project/EventPromptTab.vue'
import NotificationTab from '@/components/project/NotificationTab.vue'
import RecentEventsTab from '@/components/project/RecentEventsTab.vue'
import ProjectSidebar from '@/components/project/ProjectSidebar.vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

const route = useRoute()
const router = useRouter()
const projectId = route.params.id as string
const tabs = [
  { key: 'info', label: '项目信息' },
  { key: 'webhook-events', label: 'Webhook事件' },
  { key: 'event-prompts', label: '审查提示词' },
  { key: 'ignore-strategies', label: '忽略策略' },
  { key: 'notifications', label: '通知设置' },
  { key: 'events', label: '最近事件' },
]

const activeTab = ref('info')
const loading = ref(false)
const project = ref<any>(null)
const projectStats = ref<any>(null)
const recentEvents = ref<any[]>([])
const topContributors = ref<any[]>([])

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)
const totalEvents = ref(0)

// Notification
const notificationChannels = ref<any[]>([])
const selectedChannelIds = ref<number[]>([])
const gitlabCommentEnabled = ref(true)

// Webhook events
const webhookEventRules = ref<any[]>([])
const selectedEventIds = ref<number[]>([])

// Event prompts
const eventPrompts = ref<any[]>([])

// LLM Providers
const llmProviders = ref<any[]>([])
const ignoreStrategies = ref<any[]>([])
const ignoreStrategiesLoading = ref(false)
const selectedIgnoreStrategyStatus = ref('')
const ignoreStrategyDisableReason = ref('')
const hasEnabledIgnoreStrategies = computed(() => ignoreStrategies.value.some((item: any) => item.status !== 'disabled'))
const ignoreStrategyStatusOptions = [
  { label: '全部状态', value: '' },
  { label: '生效中', value: 'active' },
  { label: '已过期', value: 'expired' },
  { label: '已禁用', value: 'disabled' },
]

const isReviewEnabled = (value: unknown): boolean => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (!normalized) return false
    if (['true', 'yes', 'on', 'enabled', 'enable', 'active', 'open'].includes(normalized)) return true
    if (['false', 'no', 'off', 'disabled', 'disable', 'inactive', 'close', 'closed'].includes(normalized)) return false
    const numeric = Number(normalized)
    if (!Number.isNaN(numeric)) return numeric !== 0
    return true
  }
  return false
}

// --- Data loading ---

const loadProjectDetail = async () => {
  try {
    loading.value = true
    const response = await getProjectDetail(projectId)
    if (response) {
      project.value = {
        ...response,
        review_enabled: isReviewEnabled(response.review_enabled),
        ignore_strategy_enabled: isReviewEnabled(response.ignore_strategy_enabled),
      }
    }
  } catch (error) {
    console.error('Failed to load project detail:', error)
    toast.error('加载项目详情失败')
  } finally {
    loading.value = false
  }
}

const loadRecentEvents = async (page: number = 1) => {
  try {
    const response = await getProjectWebhookLogs(projectId, {
      limit: pageSize.value,
      offset: (page - 1) * pageSize.value
    })
    const logs = response?.results || []
    recentEvents.value = logs.map((log: any) => {
      const type = normalizeEventType(log.event_type)
      const payload = parsePayload(log.payload)
      const attrs = payload?.object_attributes || {}
      return {
        type,
        title: getEventTitle(type, log.merge_request_iid || attrs.iid, attrs.action),
        description: getEventDescription(type, payload),
        author: log.user_name || log.user_email || payload?.user?.name || '未知',
        branch: log.source_branch || log.target_branch || attrs.source_branch || payload?.ref?.replace(/^refs\/(heads|tags)\//, '') || '',
        status: getEventStatus(type, log.processed, payload),
        time: formatTimeAgo(log.created_at),
        merge_request_iid: log.merge_request_iid || (type === 'merge_request' ? attrs.iid : undefined),
        issue_iid: type === 'issue' ? attrs.iid : (type === 'note' ? attrs.noteable_id : undefined),
        note_id: type === 'note' ? attrs.id : undefined,
        source_branch: log.source_branch || attrs.source_branch,
        target_branch: log.target_branch || attrs.target_branch,
        tag_name: type === 'tag_push' ? payload?.ref?.replace(/^refs\/tags\//, '') : undefined,
        pipeline_id: type === 'pipeline' ? attrs.id : undefined,
        wiki_slug: type === 'wiki' ? attrs.slug : undefined,
        release_tag: type === 'release' ? (payload?.tag || payload?.name) : undefined,
        created_at: log.created_at,
      }
    })
    totalEvents.value = response?.count || logs.length
  } catch (error) {
    console.error('Failed to load recent events:', error)
  }
}

const loadReviewHistory = async () => {
  try {
    const response = await getProjectReviewHistory(projectId, { limit: 20 })
    const reviews = response?.results || []
    const contributorsMap = new Map()
    reviews.forEach((review: any) => {
      const author = review.author_name || '未知'
      if (!contributorsMap.has(author)) {
        contributorsMap.set(author, { name: author, initials: author.substring(0, 2).toUpperCase(), commits: 0 })
      }
      contributorsMap.get(author).commits++
    })
    topContributors.value = Array.from(contributorsMap.values()).sort((a, b) => b.commits - a.commits).slice(0, 5)
  } catch (error) {
    console.error('Failed to load review history:', error)
  }
}

const loadProjectStats = async () => {
  try {
    const response = await getProjectStatsDetail(projectId)
    if (response) {
      projectStats.value = response
      if (project.value) {
        project.value.commits_count = response.commits_count ?? 0
        project.value.mr_count = response.mr_count ?? 0
        project.value.members_count = response.members_count ?? 0
      }
    }
  } catch (error) {
    console.error('Failed to load project stats:', error)
  }
}

const normalizeChannelList = (data: any) => {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.results)) return data.results
  if (Array.isArray(data.channels)) return data.channels
  return []
}

const loadNotificationChannelList = async () => {
  try {
    const response = await getNotificationChannels()
    notificationChannels.value = normalizeChannelList(response)
  } catch (error) {
    console.error('Failed to load notification channels:', error)
  }
}

const loadProjectNotificationSettings = async () => {
  try {
    const response = await getProjectNotifications(projectId)
    if (response) {
      gitlabCommentEnabled.value = response.gitlab_comment_enabled !== false
      selectedChannelIds.value = Array.isArray(response.channels)
        ? response.channels.filter((item: any) => item.enabled).map((item: any) => Number(item.channel_id)).filter(Boolean)
        : []
    }
  } catch (error) {
    console.error('Failed to load project notification settings:', error)
  }
}

const loadWebhookEventRules = async () => {
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
  }
}

const loadProjectWebhookEvents = async () => {
  try {
    const response = await getProjectWebhookEvents(projectId)
    if (response) {
      const enabledIds = Array.isArray(response.enabled_webhook_events)
        ? response.enabled_webhook_events.map((id: any) => Number(id)).filter(Boolean)
        : []
      selectedEventIds.value = enabledIds.filter((id: number) =>
        webhookEventRules.value.some(rule => Number(rule.id) === id)
      )
    }
  } catch (error) {
    console.error('Failed to load project webhook events:', error)
  }
}

const loadProjectWebhookEventPrompts = async () => {
  try {
    const response = await getProjectWebhookEventPrompts(projectId)
    const existingPrompts = response?.results || []

    const promptMap = new Map<number, any>()
    existingPrompts.forEach((p: any) => promptMap.set(Number(p.event_rule), p))

    const merged: any[] = []
    for (const ruleId of selectedEventIds.value) {
      if (promptMap.has(ruleId)) {
        merged.push(promptMap.get(ruleId))
      } else {
        const rule = webhookEventRules.value.find((r: any) => Number(r.id) === ruleId)
        if (rule) {
          merged.push({
            event_rule: ruleId,
            event_rule_name: rule.name,
            event_rule_type: rule.event_type,
            event_rule_description: rule.description || '',
            custom_prompt: '',
            use_custom: false,
          })
        }
      }
    }
    eventPrompts.value = merged
  } catch (error) {
    console.error('Failed to load project webhook event prompts:', error)
  }
}

const loadLLMProviders = async () => {
  try {
    const response = await getLLMProviders()
    if (response?.results) {
      llmProviders.value = response.results
    } else if (Array.isArray(response)) {
      llmProviders.value = response
    } else {
      llmProviders.value = []
    }
  } catch (error) {
    console.error('Failed to load LLM providers:', error)
  }
}

const loadProjectIgnoreStrategies = async () => {
  try {
    ignoreStrategiesLoading.value = true
    const params: Record<string, any> = {
      project_id: Number(projectId),
    }
    if (selectedIgnoreStrategyStatus.value) {
      params.statuses = [selectedIgnoreStrategyStatus.value]
    }
    const response = await getProjectIgnoreStrategies({
      ...params,
    })
    ignoreStrategies.value = Array.isArray(response?.results) ? response.results : []
  } catch (error) {
    console.error('Failed to load project ignore strategies:', error)
    toast.error('加载忽略策略失败')
  } finally {
    ignoreStrategiesLoading.value = false
  }
}

// --- Actions ---

const goBack = () => router.push('/projects')

const toggleReview = async () => {
  if (!project.value) return
  const originalStatus = isReviewEnabled(project.value.review_enabled)
  project.value.review_enabled = !originalStatus
  try {
    if (project.value.review_enabled) {
      await enableProjectReview(project.value.project_id.toString())
      toast.success('已启用代码审查')
    } else {
      await disableProjectReview(project.value.project_id.toString())
      toast.success('已禁用代码审查')
    }
  } catch (error) {
    project.value.review_enabled = originalStatus
    console.error('Failed to toggle review:', error)
    toast.error('操作失败，请重试')
  }
}

const toggleIgnoreStrategy = async () => {
  if (!project.value) return
  const originalStatus = isReviewEnabled(project.value.ignore_strategy_enabled)
  project.value.ignore_strategy_enabled = !originalStatus
  try {
    await updateProject(project.value.project_id.toString(), {
      ignore_strategy_enabled: project.value.ignore_strategy_enabled,
    })
    if (project.value.ignore_strategy_enabled) {
      toast.success('已开启忽略策略自动生效')
    } else {
      toast.success('已关闭忽略策略自动生效')
    }
  } catch (error) {
    project.value.ignore_strategy_enabled = originalStatus
    console.error('Failed to toggle ignore strategy:', error)
    toast.error('忽略策略状态更新失败，请重试')
  }
}

const disableIgnoreStrategy = async (strategy: any) => {
  if (!strategy || strategy.status === 'disabled') return
  try {
    ignoreStrategiesLoading.value = true
    const reason = String(ignoreStrategyDisableReason.value || '').trim()
    await disableProjectIgnoreStrategy(strategy.id, reason ? { reason } : undefined)
    toast.success('已禁用策略')
    await loadProjectIgnoreStrategies()
  } catch (error) {
    console.error('Failed to disable ignore strategy:', error)
    toast.error('禁用策略失败，请重试')
  } finally {
    ignoreStrategiesLoading.value = false
  }
}

const disableAllIgnoreStrategies = async () => {
  if (!hasEnabledIgnoreStrategies.value) return
  try {
    ignoreStrategiesLoading.value = true
    const reason = String(ignoreStrategyDisableReason.value || '').trim()
    const response = await disableAllProjectIgnoreStrategies({
      project_id: Number(projectId),
      ...(reason ? { reason } : {}),
    })
    const count = Number(response?.disabled_count || 0)
    toast.success(`已禁用 ${count} 条策略`)
    await loadProjectIgnoreStrategies()
  } catch (error) {
    console.error('Failed to disable all ignore strategies:', error)
    toast.error('批量禁用失败，请重试')
  } finally {
    ignoreStrategiesLoading.value = false
  }
}

const handlePageChange = async (page: number) => {
  currentPage.value = page
  await loadRecentEvents(page)
}

const onWebhookEventsSaved = async () => {
  await loadProjectWebhookEvents()
  await loadProjectWebhookEventPrompts()
}

const refreshData = async () => {
  await Promise.all([
    loadProjectDetail(),
    loadRecentEvents(currentPage.value),
    loadReviewHistory(),
    loadProjectStats(),
    loadLLMProviders(),
    loadProjectIgnoreStrategies(),
  ])
  await loadNotificationChannelList()
  await loadProjectNotificationSettings()
  await loadWebhookEventRules()
  await loadProjectWebhookEvents()
  await loadProjectWebhookEventPrompts()
}

// --- Helpers ---

const ignoreStrategyStatusLabel = (status: string): string => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'active') return '生效中'
  if (normalized === 'expired') return '已过期'
  if (normalized === 'disabled') return '已禁用'
  return normalized || '未知'
}

const ignoreStrategyStatusSeverity = (status: string): string => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'active') return 'success'
  if (normalized === 'expired') return 'warn'
  return 'secondary'
}

const EVENT_TYPE_MAP: Record<string, string> = {
  'Merge Request Hook': 'merge_request',
  'Push Hook': 'push',
  'Note Hook': 'note',
  'Issue Hook': 'issue',
  'Tag Push Hook': 'tag_push',
  'Pipeline Hook': 'pipeline',
  'Build Hook': 'build',
  'Wiki Page Hook': 'wiki',
  'Deployment Hook': 'deployment',
  'Release Hook': 'release',
  'merge_request': 'merge_request',
  'push': 'push',
  'note': 'note',
  'issue': 'issue',
  'tag_push': 'tag_push',
  'pipeline': 'pipeline',
  'build': 'build',
  'wiki_page': 'wiki',
  'deployment': 'deployment',
  'release': 'release',
}

const normalizeEventType = (raw: string): string => {
  if (!raw) return 'unknown'
  if (EVENT_TYPE_MAP[raw]) return EVENT_TYPE_MAP[raw]
  const normalized = raw.toLowerCase().replace(/\s+hook$/i, '').replace(/\s+/g, '_')
  return normalized || 'unknown'
}

const parsePayload = (raw: any): Record<string, any> => {
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try { return JSON.parse(raw) } catch { return {} }
}

const MR_ACTION_LABEL: Record<string, string> = {
  open: '创建', update: '更新', merge: '合并', close: '关闭',
  approved: '批准', unapproved: '取消批准', reopen: '重新打开',
}

const getEventTitle = (eventType: string, mrIid?: number, action?: string) => {
  if (eventType === 'merge_request') {
    const act = action ? MR_ACTION_LABEL[action] || action : ''
    const id = mrIid ? `!${mrIid}` : ''
    return ['Merge Request', id, act].filter(Boolean).join(' ')
  }
  const map: Record<string, string> = {
    push: '代码推送',
    note: '新增评论',
    issue: 'Issue 事件',
    tag_push: '标签推送',
    pipeline: 'Pipeline 事件',
    build: '构建事件',
    wiki: 'Wiki 更新',
    deployment: '部署事件',
    release: 'Release 发布',
  }
  return map[eventType] || eventType
}

const getEventDescription = (eventType: string, payload: Record<string, any>) => {
  const attrs = payload?.object_attributes || {}
  const truncate = (s: string, max = 120) => s && s.length > max ? s.slice(0, max) + '...' : s

  switch (eventType) {
    case 'merge_request':
      return truncate(attrs.title || '') || '合并请求'
    case 'push': {
      const commits = payload?.commits
      if (Array.isArray(commits) && commits.length > 0) {
        const msg = commits[commits.length - 1]?.message?.split('\n')[0] || ''
        const count = payload.total_commits_count || commits.length
        return truncate(count > 1 ? `${count} 个提交: ${msg}` : msg) || '代码提交'
      }
      const ref = payload?.ref?.replace(/^refs\/heads\//, '') || ''
      return ref ? `推送到 ${ref}` : '代码提交'
    }
    case 'note':
      return truncate(attrs.note || '') || '评论'
    case 'issue':
      return truncate(attrs.title || '') || 'Issue'
    case 'tag_push': {
      const tag = payload?.ref?.replace(/^refs\/tags\//, '') || ''
      return tag ? `标签: ${tag}` : '标签推送'
    }
    case 'pipeline':
      return attrs.status ? `状态: ${attrs.status}` + (attrs.ref ? ` (${attrs.ref})` : '') : 'Pipeline'
    case 'build':
      return [payload?.build_name, payload?.build_status].filter(Boolean).join(' - ') || '构建'
    case 'wiki':
      return [attrs.title, attrs.action].filter(Boolean).join(' - ') || 'Wiki'
    case 'deployment':
      return [payload?.status, payload?.environment].filter(Boolean).join(' - ') || '部署'
    case 'release':
      return payload?.name || payload?.tag || 'Release'
    default:
      return 'Webhook 事件'
  }
}

const getEventStatus = (eventType: string, processed: boolean, payload?: Record<string, any>) => {
  if (!processed) return '处理中'
  const attrs = payload?.object_attributes || {}
  if (eventType === 'merge_request') {
    const action = attrs.action
    if (action === 'merge') return '已合并'
    if (action === 'close') return '已关闭'
    if (action === 'approved') return '已批准'
    return '已审查'
  }
  if (eventType === 'pipeline') {
    const s = attrs.status
    if (s === 'success') return '成功'
    if (s === 'failed') return '失败'
  }
  const map: Record<string, string> = {
    push: '已推送', note: '已评论',
    issue: '已记录', tag_push: '已推送', build: '已处理',
    wiki: '已处理', deployment: '已处理', release: '已处理',
  }
  return map[eventType] || '已处理'
}

const formatTimeAgo = (timestamp: string) => {
  const parsed = parseBackendDate(timestamp)
  if (!parsed) return '未知'
  const diff = Date.now() - parsed.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 30) return `${days} 天前`
  return formatBackendDate(timestamp)
}

onMounted(() => refreshData())
</script>
