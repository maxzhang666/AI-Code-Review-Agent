<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <span class="text-surface-500">共 {{ providers.length }} 个供应商</span>
      <Button  size="small" label="新建" @click="openCreateModal">
        <template #icon><Plus class="h-4 w-4" /></template>
      </Button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-surface-300 border-t-primary"></div>
    </div>

    <div
      v-else-if="providers.length === 0"
      class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-8 text-center"
    >
      <div class="text-surface-500">暂无 LLM 供应商配置</div>
      <div class="mt-3">
        <Button rounded label="创建第一个供应商" @click="openCreateModal">
          <template #icon><Plus class="h-4 w-4" /></template>
        </Button>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 gap-4 p-6 md:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="provider in providers"
        :key="provider.id"
        class="cursor-pointer rounded-2xl p-5 transition-all duration-200"
        :class="[
          provider.is_default
            ? 'border-2 border-primary-400 bg-gradient-to-br from-primary-50/40 to-white shadow-lg dark:border-primary-500/60 dark:from-primary-500/15 dark:to-surface-900'
            : provider.is_active
              ? 'border border-green-300/50 bg-white hover:-translate-y-0.5 hover:shadow-lg dark:border-green-500/35 dark:bg-surface-900'
              : 'border border-surface-200/50 bg-surface-50/30 opacity-70 hover:opacity-100 dark:border-surface-700/50 dark:bg-surface-800/40'
        ]"
      >
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div
              class="flex h-9 w-9 items-center justify-center rounded-xl font-bold"
              :class="getProtocolMeta(provider.protocol).iconClass"
            >
              {{ getProtocolMeta(provider.protocol).abbr }}
            </div>
            <div>
              <div class="font-semibold text-surface-900 dark:text-surface-0">{{ provider.name }}</div>
              <div class="text-2xs text-surface-500 dark:text-surface-400">{{ getProtocolMeta(provider.protocol).label }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Tag v-if="provider.is_default" severity="info">
              <template #icon><Star class="h-3 w-3" /></template>
              默认
            </Tag>
            <Tag v-if="provider.is_active" severity="success">已启用</Tag>
            <Tag v-else severity="secondary">已停用</Tag>
          </div>
        </div>

        <div class="mb-4 space-y-1">
          <div
            v-for="(line, idx) in getConfigSummary(provider)"
            :key="idx"
            class="truncate text-xs text-surface-600 dark:text-surface-300"
          >
            {{ line }}
          </div>
        </div>

        <div class="flex items-center justify-between border-t border-surface-200/30 pt-3">
          <div class="flex items-center gap-2">
            <ToggleSwitch
              :model-value="provider.is_active"
              :disabled="provider.is_default && provider.is_active"
              @update:model-value="(value: boolean) => handleSwitchChange(provider.id, value)"
            />
            <span class="text-2xs text-surface-400">{{ formatTime(provider.updated_at) }}</span>
          </div>
          <div class="flex items-center gap-1">
            <IconButton
              v-if="!provider.is_default && provider.is_active"
              size="small"
              :disabled="activatingId === provider.id"
              title="设为默认"
              aria-label="设为默认"
              @click.stop="handleActivate(provider.id)"
            >
              <RefreshCw v-if="activatingId === provider.id" class="h-3.5 w-3.5 animate-spin" />
              <Star v-else class="h-3.5 w-3.5" />
            </IconButton>
            <IconButton size="small" title="编辑" aria-label="编辑" @click.stop="openEditModal(provider)">
              <Pencil class="h-3.5 w-3.5" />
            </IconButton>
            <IconButton
              size="small"
              class="!text-red-500 hover:!text-red-600 dark:!text-red-300 dark:hover:!text-red-200"
              :disabled="provider.project_count > 0 || provider.is_default"
              :title="provider.is_default ? '默认供应商不可删除' : provider.project_count > 0 ? `被 ${provider.project_count} 个项目引用` : '删除'"
              aria-label="删除"
              @click.stop="confirmDelete(provider.id)"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </IconButton>
          </div>
        </div>
      </div>
    </div>

    <SimpleModal
      v-model="modalVisible"
      :title="editingProvider ? '编辑供应商' : '新建供应商'"
      :width="760"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <div class="grid grid-cols-1 gap-4">
          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">名称</label>
            <InputText
              v-model="form.name"
              placeholder="例如：OpenAI GPT-4"
              class="w-full"
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">协议</label>
            <Select
              :model-value="form.protocol"
              :options="protocolOptions"
              option-label="label"
              option-value="value"
              class="w-full"
              @update:model-value="onProtocolSelect"
            />
          </div>
        </div>

        <template v-if="form.protocol === 'openai_compatible'">
          <div class="grid grid-cols-1 gap-x-4 gap-y-4 md:grid-cols-2">
            <div class="space-y-1 md:col-span-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">API Base URL</label>
              <InputText
                v-model="form.config_data.api_base"
                placeholder="https://api.openai.com/v1"
                class="w-full"
              />
            </div>

            <div class="space-y-1 md:col-span-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">API Key</label>
              <InputText
                v-model="form.config_data.api_key"
                type="password"
                placeholder="sk-..."
                class="w-full"
              />
            </div>

            <div class="space-y-1 md:col-span-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">模型</label>
              <div class="flex items-center gap-2">
                <Select
                  v-model="form.config_data.model"
                  :options="modelOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="modelPlaceholder"
                  filter
                  editable
                  show-clear
                  class="min-w-0 flex-1"
                />
                <Button
                  outlined
                  rounded
                  :label="modelFetchError && !fetchingModels ? '重试' : '获取'"
                  :loading="fetchingModels"
                  class="shrink-0"
                  @click="handleFetchModels"
                >
                  <template #icon><RefreshCw class="h-4 w-4" /></template>
                </Button>
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">超时(秒)</label>
              <InputText
                v-model.number="form.config_data.timeout"
                type="number"
                min="10"
                max="600"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">请求模式</label>
              <Select
                v-model="form.config_data.request_mode"
                :options="requestModeOptions"
                option-label="label"
                option-value="value"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">最大输出 Token</label>
              <InputText
                v-model.number="form.config_data.max_tokens"
                type="number"
                min="256"
                max="65536"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">上下文窗口 Token</label>
              <InputText
                v-model.number="form.config_data.context_window"
                type="number"
                min="4096"
                max="2000000"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">提示词预留 Token</label>
              <InputText
                v-model.number="form.config_data.prompt_reserve_tokens"
                type="number"
                min="256"
                max="200000"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">输入预算安全系数</label>
              <InputText
                v-model.number="form.config_data.input_safety_ratio"
                type="number"
                min="0.1"
                max="0.95"
                step="0.01"
                class="w-full"
              />
            </div>
          </div>
        </template>

        <template v-if="form.protocol === 'claude_cli'">
          <div class="grid grid-cols-1 gap-x-4 gap-y-4 md:grid-cols-2">
            <div class="space-y-1 md:col-span-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">ANTHROPIC_BASE_URL</label>
              <InputText
                v-model="form.config_data.anthropic_base_url"
                placeholder="https://api.anthropic.com"
                class="w-full"
              />
            </div>

            <div class="space-y-1 md:col-span-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">ANTHROPIC_AUTH_TOKEN</label>
              <InputText
                v-model="form.config_data.anthropic_auth_token"
                type="password"
                placeholder="sk-ant-..."
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">CLI 路径</label>
              <InputText
                v-model="form.config_data.cli_path"
                placeholder="claude"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">超时(秒)</label>
              <InputText
                v-model.number="form.config_data.timeout"
                type="number"
                min="30"
                max="1800"
                class="w-full"
              />
            </div>
          </div>
        </template>

        <div
          v-if="form.protocol === 'mock'"
          class="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sky-700 dark:border-sky-500/35 dark:bg-sky-500/10 dark:text-sky-200"
        >
          Mock 模式无需额外配置，将返回固定的测试审查结果。
        </div>

        <div class="flex items-center justify-between gap-2 border-t border-surface-200/50 pt-3">
          <Button
            outlined
            :loading="testingConnection"
            :disabled="submitting"
            @click="handleTestConnection"
          >
            测试连接
          </Button>
          <div class="flex items-center gap-2">
            <Button outlined :disabled="submitting" @click="modalVisible = false">取消</Button>
            <Button :loading="submitting" @click="handleSubmit">确定</Button>
          </div>
        </div>
      </div>
    </SimpleModal>

    <SimpleModal
      v-model="deleteConfirmVisible"
      title="确认删除"
      :width="460"
      :mask-closable="false"
    >
      <div class="space-y-4">
        <p class="text-surface-600 dark:text-surface-300">确定要删除此 LLM 供应商配置吗？此操作不可恢复。</p>
        <div class="flex justify-end gap-2">
          <Button outlined @click="deleteConfirmVisible = false">取消</Button>
          <Button class="!bg-red-500 !border-red-500 hover:!bg-red-600 hover:!border-red-600" @click="handleDelete">
            确认删除
          </Button>
        </div>
      </div>
    </SimpleModal>

    <SimpleModal
      v-model="testResultVisible"
      title="模型连接测试结果"
      :width="920"
      :mask-closable="true"
    >
      <div class="space-y-4">
        <div
          class="rounded-xl border px-3 py-2"
          :class="testResult?.success ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-500/35 dark:bg-green-500/12 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/35 dark:bg-red-500/12 dark:text-red-300'"
        >
          {{ testResult?.message || '-' }}
        </div>

        <div class="grid grid-cols-1 gap-3 rounded-xl border border-surface-200 bg-surface-50 p-3 text-surface-700 md:grid-cols-2 dark:border-surface-700 dark:bg-surface-800/70 dark:text-surface-200">
          <div>协议：{{ testResult?.details?.protocol || '-' }}</div>
          <div>模型：{{ testResult?.details?.model || '-' }}</div>
          <div>耗时(ms)：{{ testResult?.details?.duration_ms ?? '-' }}</div>
          <div>回复字符数：{{ testResult?.details?.content_length ?? '-' }}</div>
        </div>

        <div>
          <div class="mb-2 text-sm font-medium text-surface-700">模型回复文本</div>
          <Textarea
            :model-value="testResultContentText"
            rows="5"
            readonly
            class="w-full text-xs"
          />
        </div>

        <div>
          <div class="mb-2 font-medium text-surface-700">完整 Response 信息</div>
          <Textarea
            :model-value="testResultRawResponseText"
            rows="14"
            readonly
            class="w-full font-mono text-xs"
          />
        </div>

        <div class="flex justify-end">
          <Button outlined @click="testResultVisible = false">关闭</Button>
        </div>
      </div>
    </SimpleModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Pencil, Plus, RefreshCw, Star, Trash2 } from 'lucide-vue-next'
import {
  activateLLMProvider,
  createLLMProvider,
  deleteLLMProvider,
  fetchLLMModels,
  getLLMProviders,
  patchLLMProvider,
  testLLMProviderConnection,
  updateLLMProvider,
} from '@/api'
import { parseBackendDate } from '@/utils/datetime'
import { toast } from '@/utils/toast'
import IconButton from '@/components/ui/IconButton.vue'
import ToggleSwitch from 'primevue/toggleswitch'
import SimpleModal from '@/components/ui/SimpleModal.vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

interface LLMProviderItem {
  id: number
  name: string
  protocol: string
  is_active: boolean
  is_default: boolean
  config_data: Record<string, any>
  project_count: number
  created_at: string | null
  updated_at: string | null
}

interface TestConnectionResult {
  success: boolean
  message: string
  details: Record<string, any>
}

const providers = ref<LLMProviderItem[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const deleteConfirmVisible = ref(false)
const testResultVisible = ref(false)
const submitting = ref(false)
const testingConnection = ref(false)
const activatingId = ref<number | null>(null)
const editingProvider = ref<LLMProviderItem | null>(null)
const deleteTargetId = ref<number | null>(null)

const modelList = ref<string[]>([])
const fetchingModels = ref(false)
const modelFetchError = ref('')
const modelFetchedOnce = ref(false)
const testResult = ref<TestConnectionResult | null>(null)

const resetModelFetchState = () => {
  modelList.value = []
  fetchingModels.value = false
  modelFetchError.value = ''
  modelFetchedOnce.value = false
}

const modelPlaceholder = computed(() => {
  if (fetchingModels.value) return '获取中...'
  if (modelFetchError.value) return '获取失败，可手动输入'
  if (modelFetchedOnce.value && modelList.value.length === 0) return '未找到模型，可手动输入'
  if (modelFetchedOnce.value) return '搜索或选择模型'
  return '请先获取模型列表'
})

const modelOptions = computed(() => {
  const options = modelList.value.map((model) => ({ label: model, value: model }))
  const current = String(form.value.config_data.model || '').trim()
  if (current && !options.some((item) => item.value === current)) {
    options.unshift({ label: current, value: current })
  }
  return options
})

const stringifyForDisplay = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const testResultContentText = computed(() => stringifyForDisplay(testResult.value?.details?.content || '-'))
const testResultRawResponseText = computed(() => stringifyForDisplay(testResult.value?.details?.raw_response || '-'))

const protocolOptions = [
  { value: 'openai_compatible', label: 'OpenAI Compatible' },
  { value: 'claude_cli', label: 'Claude CLI' },
  { value: 'mock', label: 'Mock (测试)' },
]

const requestModeOptions = [
  { value: 'auto', label: '自动（按模型识别）' },
  { value: 'responses', label: 'Responses' },
  { value: 'chat_completions', label: 'Chat Completions' },
]

const PROTOCOL_META: Record<string, { label: string; abbr: string; iconClass: string }> = {
  openai_compatible: { label: 'OpenAI Compatible', abbr: 'OA', iconClass: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' },
  claude_cli: { label: 'Claude CLI', abbr: 'CL', iconClass: 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300' },
  mock: { label: 'Mock', abbr: 'MK', iconClass: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-300' },
}

const getProtocolMeta = (protocol: string) => {
  return PROTOCOL_META[protocol] || { label: protocol, abbr: '??', iconClass: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-300' }
}

const getDefaultConfigData = (protocol: string): Record<string, any> => {
  switch (protocol) {
    case 'openai_compatible':
      return {
        model: '',
        api_base: '',
        api_key: '',
        timeout: 300,
        request_mode: 'auto',
        max_tokens: 20480,
        context_window: 128000,
        prompt_reserve_tokens: 3000,
        input_safety_ratio: 0.75,
      }
    case 'claude_cli':
      return {
        anthropic_base_url: '',
        anthropic_auth_token: '',
        cli_path: 'claude',
        timeout: 300,
      }
    case 'mock':
      return {}
    default:
      return {}
  }
}

const form = ref({
  name: '',
  protocol: 'openai_compatible',
  config_data: getDefaultConfigData('openai_compatible') as Record<string, any>,
})

const getConfigSummary = (provider: LLMProviderItem): string[] => {
  const c = provider.config_data || {}
  switch (provider.protocol) {
    case 'openai_compatible':
      return [
        c.model ? `模型: ${c.model}` : '',
        c.api_base ? `API: ${c.api_base}` : '',
        c.request_mode ? `请求模式: ${c.request_mode}` : '',
        c.max_tokens ? `最大输出: ${c.max_tokens}` : '',
        c.context_window ? `上下文: ${c.context_window}` : '',
        c.input_safety_ratio ? `安全系数: ${c.input_safety_ratio}` : '',
      ].filter(Boolean)
    case 'claude_cli':
      return [
        c.cli_path ? `CLI: ${c.cli_path}` : '',
        c.anthropic_base_url ? `URL: ${c.anthropic_base_url}` : '',
      ].filter(Boolean)
    case 'mock':
      return ['模拟模式']
    default:
      return [provider.protocol]
  }
}

const formatTime = (ts: string | null) => {
  if (!ts) return ''
  const parsed = parseBackendDate(ts)
  if (!parsed) return ts
  return parsed.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const fetchProviders = async () => {
  loading.value = true
  try {
    const res = await getLLMProviders()
    const data = res?.results ?? res?.data?.results ?? (Array.isArray(res) ? res : [])
    providers.value = data
  } catch (error) {
    console.error('Failed to load LLM providers:', error)
    toast.error('加载 LLM 供应商失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingProvider.value = null
  form.value = {
    name: '',
    protocol: 'openai_compatible',
    config_data: getDefaultConfigData('openai_compatible'),
  }
  resetModelFetchState()
  modalVisible.value = true
}

const openEditModal = (provider: LLMProviderItem) => {
  editingProvider.value = provider
  form.value = {
    name: provider.name,
    protocol: provider.protocol,
    config_data: { ...getDefaultConfigData(provider.protocol), ...provider.config_data },
  }
  resetModelFetchState()
  modalVisible.value = true
}

const handleProtocolChange = (protocol: string) => {
  form.value.config_data = getDefaultConfigData(protocol)
  resetModelFetchState()
}

const onProtocolSelect = (value: unknown) => {
  const protocol = String(value || '')
  form.value.protocol = protocol
  handleProtocolChange(protocol)
}

const handleFetchModels = async () => {
  const apiBase = form.value.config_data.api_base?.trim()
  if (!apiBase) {
    toast.warning('请先填写 API Base URL')
    return
  }

  fetchingModels.value = true
  modelFetchError.value = ''
  try {
    const res = await fetchLLMModels({
      api_base: apiBase,
      api_key: form.value.config_data.api_key || '',
    })
    const models = res?.models ?? res?.data?.models ?? []
    modelList.value = models
    modelFetchedOnce.value = true
    if (models.length > 0) {
      toast.success(`已加载 ${models.length} 个模型`)
    } else {
      toast.warning('未找到可用模型，请手动输入')
    }
  } catch (error: any) {
    modelFetchError.value = error?.response?.data?.message || error?.response?.data?.detail || error?.message || '获取模型失败'
    toast.error(modelFetchError.value)
  } finally {
    fetchingModels.value = false
  }
}

const handleTestConnection = async () => {
  if (testingConnection.value) return

  if (form.value.protocol === 'openai_compatible' && !form.value.config_data.api_base?.trim()) {
    toast.warning('请先填写 API Base URL')
    return
  }
  if (form.value.protocol === 'openai_compatible' && !form.value.config_data.model?.trim()) {
    toast.warning('请先填写模型名称')
    return
  }

  testingConnection.value = true
  try {
    const res = await testLLMProviderConnection({
      protocol: form.value.protocol,
      config_data: form.value.config_data || {},
    })
    const payload = (res?.data ?? res ?? {}) as TestConnectionResult
    const success = Boolean(payload?.success)
    const message = String(payload?.message ?? (success ? '连接测试通过' : '连接测试失败'))
    testResult.value = {
      success,
      message,
      details: (payload?.details && typeof payload.details === 'object') ? payload.details : {},
    }
    testResultVisible.value = true
  } catch (error: any) {
    const message = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '连接测试失败'
    testResult.value = { success: false, message: String(message), details: {} }
    testResultVisible.value = true
  } finally {
    testingConnection.value = false
  }
}

const handleSubmit = async () => {
  if (!form.value.name.trim()) {
    toast.error('请填写供应商名称')
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      protocol: form.value.protocol,
      is_active: editingProvider.value?.is_active ?? false,
      config_data: form.value.config_data,
    }
    if (editingProvider.value) {
      await updateLLMProvider(editingProvider.value.id, payload)
      toast.success('供应商已更新')
    } else {
      await createLLMProvider(payload)
      toast.success('供应商已创建')
    }
    modalVisible.value = false
    await fetchProviders()
  } catch (error: any) {
    const message = error?.response?.data?.detail || error?.message || '操作失败'
    toast.error(message)
  } finally {
    submitting.value = false
  }
}

const handleActivate = async (id: number) => {
  activatingId.value = id
  try {
    await activateLLMProvider(id)
    toast.success('已设为默认供应商')
    await fetchProviders()
  } catch {
    toast.error('设为默认失败')
  } finally {
    activatingId.value = null
  }
}

const handleToggleActive = async (id: number, active: boolean) => {
  const target = providers.value.find((p) => p.id === id)
  if (!target) return
  target.is_active = active
  try {
    await patchLLMProvider(id, { is_active: active })
    toast.success(active ? '供应商已启用' : '供应商已停用')
  } catch {
    target.is_active = !active
    toast.error('操作失败')
  }
}

const handleSwitchChange = (id: number, value: boolean) => {
  void handleToggleActive(id, value)
}

const confirmDelete = (id: number) => {
  deleteTargetId.value = id
  deleteConfirmVisible.value = true
}

const handleDelete = async () => {
  if (!deleteTargetId.value) return
  try {
    await deleteLLMProvider(deleteTargetId.value)
    toast.success('供应商已删除')
    deleteConfirmVisible.value = false
    await fetchProviders()
  } catch {
    toast.error('删除失败')
  }
}

onMounted(fetchProviders)
</script>
