<template>
  <div>
    <Card>
      <template #content>
        <div class="space-y-6">
          <div class="flex items-center gap-3">
            <div class="h-2 w-2 rounded-full bg-purple-500"></div>
            <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">Webhook 事件规则</h3>
          </div>

          <div class="rounded-xl border border-surface-200/40 bg-surface-50/50 p-4 text-surface-600 dark:border-surface-700/50 dark:bg-surface-800/60 dark:text-surface-300">
            管理全局 Webhook 事件识别规则。当前仅支持 Merge Request 创建和更新两种场景。
          </div>

          <div class="flex items-center justify-between">
            <h4 class="font-semibold text-surface-900 dark:text-surface-100">事件规则列表</h4>
            <Button :loading="initializing" @click="initializeDefaultRules" size="small">
              {{ initializing ? '初始化中...' : '初始化默认规则' }}
            </Button>
          </div>

          <div
            v-if="filteredRules.length === 0"
            class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-8 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/60 dark:text-surface-400"
          >
            暂无事件规则，请点击「初始化默认规则」开始配置。
          </div>

          <div v-else class="space-y-4">
            <Card v-for="rule in filteredRules" :key="rule.id" class="!shadow-sm">
              <template #content>
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 space-y-2">
                    <div class="flex items-center gap-2">
                      <div class="font-semibold text-surface-900 dark:text-surface-100">{{ rule.name }}</div>
                      <Tag v-if="!rule.is_active" severity="secondary">停用</Tag>
                    </div>
                    <div class="text-xs text-surface-500 dark:text-surface-400">{{ rule.description || '暂无描述' }}</div>
                    <div class="space-y-1 text-xs text-surface-400">
                      <div>事件类型：{{ rule.event_type }}</div>
                      <pre class="overflow-x-auto rounded bg-surface-50 p-2 text-xs font-mono dark:bg-surface-800 dark:text-surface-300">匹配规则：{{ JSON.stringify(rule.match_rules, null, 2) }}</pre>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-3 pt-3">
                  <Button size="small" outlined label="编辑" @click="editRule(rule)">
                    <template #icon><Pencil class="h-4 w-4" /></template>
                  </Button>
                  <Button size="small" text label="测试" @click="testRule(rule)">
                    <template #icon><Play class="h-4 w-4" /></template>
                  </Button>
                </div>
              </template>
            </Card>
          </div>
        </div>
      </template>
    </Card>

    <SimpleModal
      v-model="ruleEditorVisible"
      title="编辑事件规则"
      :width="640"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">规则名称</label>
            <InputText
              v-model="editingRule.name"
              placeholder="输入规则名称"
            />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">事件类型</label>
            <Select
              v-model="editingRule.event_type"
              :options="eventTypeOptions"
              option-label="label"
              option-value="value"
              disabled
            />
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-xs font-medium uppercase tracking-wide text-surface-500">描述</label>
          <Textarea
            v-model="editingRule.description"
            rows="3"
            placeholder="输入规则描述"
          />
        </div>

        <div class="space-y-1">
          <label class="text-xs font-medium uppercase tracking-wide text-surface-500">匹配规则 (JSON 格式)</label>
          <Textarea
            v-model="editingRule.matchRulesText"
            rows="8"
            placeholder="输入匹配规则，JSON格式"
            class="font-mono text-xs"
          />
        </div>

        <label class="inline-flex items-center gap-2 text-surface-700">
          <Checkbox v-model="editingRule.is_active" binary />
          启用此规则
        </label>

        <div class="flex justify-end gap-3 pt-2">
          <Button outlined @click="ruleEditorVisible = false">取消</Button>
          <Button :loading="ruleSaving" @click="saveRule">
            {{ ruleSaving ? '保存中...' : '保存规则' }}
          </Button>
        </div>
      </div>
    </SimpleModal>

    <SimpleModal
      v-model="testDialogVisible"
      title="测试事件规则"
      :width="640"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div class="space-y-1">
          <label class="text-xs font-medium uppercase tracking-wide text-surface-500">测试 Payload (JSON 格式)</label>
          <Textarea
            v-model="testPayload"
            rows="12"
            placeholder="粘贴要测试的 GitLab Webhook Payload"
            class="font-mono text-xs"
          />
        </div>

        <div
          v-if="testResult"
          class="rounded-xl border p-3"
          :class="testResult.is_match ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-500/35 dark:bg-green-500/12 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/35 dark:bg-red-500/12 dark:text-red-300'"
        >
          <div class="font-semibold">{{ testResult.is_match ? '匹配成功' : '匹配失败' }}</div>
          <div class="mt-1">规则：{{ testResult.rule_name }}</div>
          <div>{{ testResult.is_match ? '该 payload 匹配当前规则。' : '该 payload 不匹配当前规则。' }}</div>
        </div>

        <div class="flex justify-end gap-3">
          <Button outlined @click="testDialogVisible = false">关闭</Button>
          <Button :disabled="!testPayload.trim()" @click="executeTest">开始测试</Button>
        </div>
      </div>
    </SimpleModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Pencil, Play } from 'lucide-vue-next'
import {
  initializeDefaultWebhookEventRules,
  testWebhookEventRule,
  updateWebhookEventRule,
} from '@/api/index'
import { toast } from '@/utils/toast'
import SimpleModal from '@/components/ui/SimpleModal.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

const props = defineProps<{ rules: any[] }>()
const emit = defineEmits<{ refreshRules: [] }>()

const normalize = (value: unknown) => String(value ?? '').trim().toLowerCase()

const isSupportedWebhookRule = (rule: any) => {
  const eventType = normalize(rule?.event_type)
  if (eventType === 'mr_open' || eventType === 'mr_update') return true
  if (eventType !== 'merge request hook') return false
  const action = normalize(rule?.match_rules?.object_attributes?.action)
  return action === 'open' || action === 'update'
}

const filteredRules = computed(() => props.rules.filter(isSupportedWebhookRule))
const eventTypeOptions = [
  { label: 'MR 创建', value: 'mr_open' },
  { label: 'MR 更新', value: 'mr_update' },
]

const initializing = ref(false)
const ruleEditorVisible = ref(false)
const ruleSaving = ref(false)
const editingRule = ref({
  id: null as number | null,
  name: '',
  event_type: 'mr_open',
  description: '',
  matchRulesText: '',
  is_active: true,
})

const testDialogVisible = ref(false)
const testPayload = ref('')
const testResult = ref<any>(null)
const currentTestRule = ref<any>(null)

const initializeDefaultRules = async () => {
  const confirmed = window.confirm('系统将创建 2 条 Merge Request 事件规则：MR 创建和 MR 更新，确认继续吗？')
  if (!confirmed) return

  initializing.value = true
  try {
    await initializeDefaultWebhookEventRules()
    emit('refreshRules')
    toast.success('默认规则初始化完成')
  } catch (error) {
    console.error('Failed to initialize default rules:', error)
    toast.error('初始化默认规则失败')
  } finally {
    initializing.value = false
  }
}

const editRule = (rule: any) => {
  editingRule.value = {
    id: rule.id,
    name: rule.name,
    event_type: rule.event_type,
    description: rule.description || '',
    matchRulesText: JSON.stringify(rule.match_rules, null, 2),
    is_active: rule.is_active !== false,
  }
  ruleEditorVisible.value = true
}

const saveRule = async () => {
  if (!editingRule.value.id) return
  if (!editingRule.value.name.trim()) {
    toast.warning('请输入规则名称')
    return
  }

  let matchRules: any
  try {
    matchRules = JSON.parse(editingRule.value.matchRulesText)
  } catch {
    toast.error('匹配规则必须是合法 JSON')
    return
  }

  ruleSaving.value = true
  try {
    await updateWebhookEventRule(editingRule.value.id, {
      name: editingRule.value.name,
      event_type: editingRule.value.event_type,
      description: editingRule.value.description,
      match_rules: matchRules,
      is_active: editingRule.value.is_active,
    })
    ruleEditorVisible.value = false
    emit('refreshRules')
    toast.success('规则保存成功')
  } catch (error) {
    console.error('Failed to save event rule:', error)
    toast.error('保存规则失败')
  } finally {
    ruleSaving.value = false
  }
}

const testRule = (rule: any) => {
  currentTestRule.value = rule
  testResult.value = null
  testPayload.value = JSON.stringify(
    {
      object_kind: 'merge_request',
      object_attributes: { action: 'open', iid: 1, title: 'Test MR' },
      project: { id: 123, name: 'test-project' },
    },
    null,
    2,
  )
  testDialogVisible.value = true
}

const executeTest = async () => {
  if (!testPayload.value.trim() || !currentTestRule.value?.id) return

  let payload: any
  try {
    payload = JSON.parse(testPayload.value)
  } catch {
    toast.error('测试 Payload 必须是合法 JSON')
    return
  }

  try {
    const result = await testWebhookEventRule(currentTestRule.value.id, payload)
    const data = result?.data ?? result
    testResult.value = {
      rule_name: currentTestRule.value.name,
      is_match: Boolean(data?.is_match),
      payload: data?.payload,
      match_rules: data?.match_rules,
    }
  } catch (error) {
    console.error('Failed to test rule:', error)
    toast.error('测试规则失败')
  }
}
</script>
