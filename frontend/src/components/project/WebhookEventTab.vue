<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
              <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-0">LLM 模型配置</h3>
            </div>
            <Button
              rounded
              label="保存"
              :loading="savingProvider"
              :disabled="!providerChanged"
              @click="saveProvider"
            >
              <template #icon><Save class="w-4 h-4" /></template>
            </Button>
          </div>

          <div class="bg-surface-50/50 border border-surface-200/40 rounded-xl p-4 text-surface-600 dark:bg-surface-800/60 dark:border-surface-700/50 dark:text-surface-300">
            为该项目指定 LLM 供应商，不同项目可使用不同模型进行代码审查。未指定时使用系统默认供应商。
          </div>

          <Select
            v-model="selectedProviderValue"
            :options="providerOptions"
            option-label="label"
            option-value="value"
          />
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
              <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-0">Webhook 事件配置</h3>
            </div>
            <Button rounded label="保存" :loading="saving" @click="save">
              <template #icon><Save class="w-4 h-4" /></template>
            </Button>
          </div>

          <div class="bg-surface-50/50 border border-surface-200/40 rounded-xl p-4 text-surface-600 dark:bg-surface-800/60 dark:border-surface-700/50 dark:text-surface-300">
            选择触发代码审查的 Webhook 事件。只有选中的事件类型才会触发自动代码审查。
          </div>

          <div v-if="webhookEventRules.length === 0" class="p-6 bg-surface-50 border border-dashed border-surface-200 text-center rounded-xl text-surface-500 dark:bg-surface-800/60 dark:border-surface-700 dark:text-surface-400">
            暂无可用的 Webhook 事件规则，请在配置管理中创建。
          </div>

          <div v-else class="space-y-3">
            <label
              v-for="rule in webhookEventRules"
              :key="rule.id"
              class="flex items-start gap-3 p-4 rounded-xl transition-all duration-200"
              :class="[
                localSelectedIds.includes(Number(rule.id))
                  ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-500 shadow-md hover:shadow-lg cursor-pointer dark:from-green-500/12 dark:to-emerald-500/12 dark:border-green-400'
                  : 'bg-white border border-surface-200/60 hover:border-surface-300 cursor-pointer dark:bg-surface-900 dark:border-surface-700/60 dark:hover:border-surface-600',
                !rule.is_active && 'opacity-60 cursor-not-allowed'
              ]"
            >
              <Checkbox
                binary
                :model-value="localSelectedIds.includes(Number(rule.id))"
                :disabled="!rule.is_active"
                class="mt-1"
                @update:model-value="(value: boolean) => toggleRule(Number(rule.id), Boolean(value))"
              />
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <div
                    class="font-semibold"
                    :class="localSelectedIds.includes(Number(rule.id)) ? 'text-green-900 dark:text-green-200' : 'text-surface-900 dark:text-surface-0'"
                  >
                    {{ rule.name }}
                  </div>
                  <Tag v-if="localSelectedIds.includes(Number(rule.id))" severity="success">
                    <template #icon><CheckCircle2 class="w-3 h-3" /></template>
                    已启用
                  </Tag>
                  <Tag v-else-if="!rule.is_active" severity="secondary">停用</Tag>
                  <Tag :severity="localSelectedIds.includes(Number(rule.id)) ? 'success' : 'secondary'">
                    {{ rule.event_type }}
                  </Tag>
                </div>
                <div
                  class="text-xs mb-2"
                  :class="localSelectedIds.includes(Number(rule.id)) ? 'text-green-700 dark:text-green-300' : 'text-surface-600 dark:text-surface-300'"
                >
                  {{ rule.description || '暂无描述' }}
                </div>
                <div
                  class="text-xs font-mono p-2 rounded"
                  :class="localSelectedIds.includes(Number(rule.id)) ? 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-500/12 dark:text-green-300 dark:border-green-500/35' : 'bg-surface-50 text-surface-500 dark:bg-surface-800 dark:text-surface-400'"
                >
                  {{ JSON.stringify(rule.match_rules) }}
                </div>
              </div>
            </label>
          </div>

          <div v-if="localSelectedIds.length > 0" class="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-400 rounded-xl p-4 shadow-sm dark:from-green-500/12 dark:to-emerald-500/12 dark:border-green-500/40">
            <div class="flex items-center gap-2 mb-2">
              <CheckCircle2 class="w-5 h-5 text-green-600 dark:text-green-300" />
              <div class="font-semibold text-green-900 dark:text-green-200">已选择 {{ localSelectedIds.length }} 个事件</div>
            </div>
            <div class="text-xs text-green-700 dark:text-green-300">这些事件将触发自动代码审查</div>
          </div>
          <div v-else class="bg-orange-50 border border-orange-200 rounded-xl p-4 dark:bg-orange-500/10 dark:border-orange-500/35">
            <div class="flex items-center gap-2 mb-2">
              <AlertCircle class="w-5 h-5 text-orange-600 dark:text-orange-300" />
              <div class="edium text-orange-900 dark:text-orange-200">未选择任何事件</div>
            </div>
            <div class="text-xs text-orange-700 dark:text-orange-300">请至少选择一个事件以启用自动代码审查</div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Save, CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { updateProjectWebhookEvents, updateProject } from '@/api'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const props = defineProps<{
  projectId: string
  webhookEventRules: any[]
  selectedEventIds: number[]
  project: any
  llmProviders: any[]
}>()

const emit = defineEmits<{
  saved: []
  'update:selectedEventIds': [ids: number[]]
  providerSaved: []
}>()

const localSelectedIds = ref<number[]>([...props.selectedEventIds])
const saving = ref(false)

const selectedProviderId = ref<number | null>(null)
const savingProvider = ref(false)

const activeProviders = computed(() =>
  (props.llmProviders || []).filter((p: any) => p.is_active)
)

const selectedProviderValue = computed<string>({
  get: () => (selectedProviderId.value == null ? '' : String(selectedProviderId.value)),
  set: (value) => {
    selectedProviderId.value = value === '' ? null : Number(value)
  }
})

const defaultProviderName = computed(() => {
  const dp = (props.llmProviders || []).find((p: any) => p.is_default && p.is_active)
  return dp ? dp.name : ''
})

const providerOptions = computed(() => {
  const options = [{
    label: `跟随全局配置${defaultProviderName.value ? `（${defaultProviderName.value}）` : ''}`,
    value: '',
  }]
  activeProviders.value.forEach((provider: any) => {
    options.push({
      label: `${provider.name} (${protocolLabel(provider.protocol)})`,
      value: String(provider.id),
    })
  })
  return options
})

const providerChanged = computed(() => {
  const current = props.project?.default_llm_provider_id ?? null
  return selectedProviderId.value !== current
})

watch(() => props.project, (val) => {
  if (val) {
    selectedProviderId.value = val.default_llm_provider_id ?? null
  }
}, { immediate: true })

const protocolLabel = (protocol: string) => {
  const labels: Record<string, string> = {
    openai_compatible: 'OpenAI',
    anthropic_api: 'Anthropic',
    claude_cli: 'Claude CLI',
    ollama_api: 'Ollama',
    mock: 'Mock',
  }
  return labels[protocol] || protocol
}

const saveProvider = async () => {
  savingProvider.value = true
  try {
    await updateProject(props.projectId, {
      default_llm_provider_id: selectedProviderId.value ?? 0,
    })
    toast.success('LLM 模型配置已保存')
    emit('providerSaved')
  } catch (error) {
    console.error('Failed to save LLM provider:', error)
    toast.error('保存失败，请重试')
  } finally {
    savingProvider.value = false
  }
}

watch(() => props.selectedEventIds, (ids) => {
  localSelectedIds.value = [...ids]
})

const toggleRule = (id: number, checked: boolean) => {
  if (checked) {
    if (!localSelectedIds.value.includes(id)) {
      localSelectedIds.value = [...localSelectedIds.value, id]
    }
  } else {
    localSelectedIds.value = localSelectedIds.value.filter((item) => item !== id)
  }
}

const save = async () => {
  saving.value = true
  try {
    const normalizedIds = Array.from(new Set(localSelectedIds.value.map((id) => Number(id)))).filter((id) => !Number.isNaN(id))
    await updateProjectWebhookEvents(props.projectId, { enabled_webhook_events: normalizedIds })
    toast.success('Webhook事件配置已更新')
    emit('update:selectedEventIds', normalizedIds)
    emit('saved')
  } catch (error) {
    console.error('Failed to save project webhook events:', error)
    toast.error('保存Webhook事件配置失败')
  } finally {
    saving.value = false
  }
}
</script>
