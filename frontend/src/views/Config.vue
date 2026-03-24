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
      <span>{{ message }}</span>
      <IconButton
        size="small"
        class="!h-6 !w-6 !text-current/70"
        aria-label="关闭提示"
        @click="message = ''"
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
import { computed, ref, onMounted } from 'vue'
import {
  getConfigSummary,
  batchUpdateConfig,
  getSystemConfigs,
  updateSystemConfigs,
  getNotificationChannels,
  getWebhookEventRules
} from '@/api/index'
import GitLabConfigTab from '@/components/config/GitLabConfigTab.vue'
import LLMProviderTab from '@/components/config/LLMProviderTab.vue'
import WebhookEventRulesTab from '@/components/config/WebhookEventRulesTab.vue'
import NotificationChannelsTab from '@/components/config/NotificationChannelsTab.vue'
import AuthUsersTab from '@/components/config/AuthUsersTab.vue'
import ReviewSnippetConfigTab from '@/components/config/ReviewSnippetConfigTab.vue'
import IconButton from '@/components/ui/IconButton.vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

const activeTab = ref('gitlab')
const tabs = [
  { key: 'gitlab', label: 'GitLab 配置' },
  { key: 'llm-providers', label: 'LLM 供应商' },
  { key: 'review-snippet', label: '问题代码' },
  { key: 'webhook-events', label: 'Webhook 事件' },
  { key: 'notification', label: '通知配置' },
  { key: 'auth-users', label: '账号管理' },
]
const saving = ref(false)
const savingSystemConfig = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const config = ref({
  llm: { provider: 'openai', model: 'gpt-4', apiKey: '', apiBase: '' },
  gitlab: { serverUrl: 'https://gitlab.com', privateToken: '', siteUrl: '' },
  system: { reviewCodeSnippetSource: 'line' as 'line' | 'llm' },
})

const channels = ref<any[]>([])
const webhookEventRules = ref<any[]>([])
const originalConfig = ref({})

const normalizeReviewCodeSnippetSource = (value: unknown): 'line' | 'llm' => {
  const normalized = String(value || '').trim().toLowerCase()
  return normalized === 'llm' ? 'llm' : 'line'
}

const isSystemConfigDirty = computed(() => {
  const original = JSON.parse(JSON.stringify(originalConfig.value || {}))
  const originalSource = normalizeReviewCodeSnippetSource(original?.system?.reviewCodeSnippetSource)
  return config.value.system.reviewCodeSnippetSource !== originalSource
})

const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 3000)
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
      const sourceConfig = systemConfigList.find(
        (item: any) => String(item?.key || '') === 'review.code_snippet_source'
      )
      config.value.system.reviewCodeSnippetSource = normalizeReviewCodeSnippetSource(sourceConfig?.value)
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

onMounted(() => loadConfig())
</script>
