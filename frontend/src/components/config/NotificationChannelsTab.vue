<template>
  <div>
    <Card>
      <template #content>
        <div class="space-y-6">
          <div class="flex items-center gap-3">
            <div class="h-2 w-2 rounded-full bg-green-500"></div>
            <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">通知配置</h3>
          </div>

          <div class="rounded-xl border border-surface-200/40 bg-surface-50/50 p-4 text-surface-600 dark:border-surface-700/50 dark:bg-surface-800/60 dark:text-surface-300">
            管理全局通知通道（钉钉/飞书/企业微信/Slack/邮件）。GitLab 评论请在项目详情页的通知设置中单独控制。
          </div>

          <div class="flex items-center justify-between">
            <h4 class="font-semibold text-surface-900 dark:text-surface-100">通道列表</h4>
            <Button label="新建通道" @click="openDialog()" size="small">
              <template #icon><PlusCircle class="h-4 w-4" /></template>
            </Button>
          </div>

          <div
            v-if="visibleChannels.length === 0"
            class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-8 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/60 dark:text-surface-400"
          >
            暂无通知通道，请点击「新建通道」开始配置。
          </div>

          <div v-else class="space-y-6">
            <div v-for="type in channelTypes" :key="type.value" class="space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 edium text-surface-900 dark:text-surface-100">
                  <img v-if="channelIcons[type.value]" :src="channelIcons[type.value]" :alt="type.label" class="h-5 w-5 object-contain" >
                  <span>{{ type.label }}</span>
                </div>
                <Button text size="small" label="新增" @click="openDialog(type.value)">
                  <template #icon><PlusCircle class="h-3 w-3" /></template>
                </Button>
              </div>

              <div v-if="grouped[type.value]?.length" class="space-y-3">
                <Card v-for="channel in grouped[type.value]" :key="channel.id" class="!shadow-sm">
                  <template #content>
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex items-start gap-2">
                        <img
                          v-if="channelIcons[channel.notification_type]"
                          :src="channelIcons[channel.notification_type]"
                          :alt="channel.notification_type"
                          class="mt-0.5 h-6 w-6 shrink-0 object-contain"
                        >
                        <div>
                          <div class="font-semibold text-surface-900 dark:text-surface-100">{{ channel.name }}</div>
                          <div class="mt-1 text-xs text-surface-500 dark:text-surface-400">{{ channel.description || '暂无备注' }}</div>
                        </div>
                      </div>
                      <div class="flex items-center gap-2">
                        <Tag v-if="channel.is_default" severity="success">默认</Tag>
                        <Tag v-if="channel.is_active === false" severity="secondary">停用</Tag>
                      </div>
                    </div>
                    <div class="mt-2 text-xs text-surface-500 dark:text-surface-400">
                      <div v-if="channel.webhook_url">Webhook：{{ channel.webhook_url }}</div>
                      <div v-else>未配置 Webhook</div>
                    </div>
                    <div class="flex items-center gap-3 pt-3">
                      <Button size="small" outlined label="编辑" @click="editChannel(channel)">
                        <template #icon><Pencil class="h-4 w-4" /></template>
                      </Button>
                      <Button size="small" text :label="testingId === channel.id ? '发送中...' : '测试'" :loading="testingId === channel.id" @click="testChannel(channel)">
                        <template #icon><Play class="h-4 w-4" /></template>
                      </Button>
                      <Button severity="danger" size="small" text label="删除" @click="removeChannel(channel)">
                        <template #icon><Trash2 class="h-4 w-4" /></template>
                      </Button>
                    </div>
                  </template>
                </Card>
              </div>
              <div v-else class="rounded-xl bg-surface-50 px-3 py-2 text-xs text-surface-500 dark:bg-surface-800/60 dark:text-surface-400">暂无 {{ type.label }} 通道</div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <SimpleModal
      v-model="dialogVisible"
      :title="form.id ? '编辑通知通道' : '新建通知通道'"
      :width="640"
      :mask-closable="false"
      @close="closeDialog"
    >
      <div class="space-y-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">通道名称</label>
            <InputText
              v-model="form.name"
              placeholder="用于区分不同项目的通道名称"
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">通道类型</label>
            <Select
              v-model="form.notification_type"
              :options="channelTypes"
              option-label="label"
              option-value="value"
              :disabled="form.id !== null"
            />
            <div v-if="channelIcons[form.notification_type]" class="mt-2 flex items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
              <img :src="channelIcons[form.notification_type]" :alt="form.notification_type" class="h-5 w-5 object-contain" >
              <span>{{ baseLabels[form.notification_type] }}</span>
            </div>
          </div>

          <div class="space-y-1 md:col-span-2">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">备注</label>
            <Textarea
              v-model="form.description"
              rows="3"
              placeholder="补充说明该通道的使用场景"
            />
          </div>

          <div v-if="['dingtalk', 'feishu', 'slack', 'wechat'].includes(form.notification_type)" class="space-y-1 md:col-span-2">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">Webhook URL</label>
            <InputText
              v-model="form.webhook_url"
              placeholder="https://"
            />
          </div>

          <div v-if="['dingtalk', 'feishu'].includes(form.notification_type)" class="space-y-1 md:col-span-2">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">Secret (可选)</label>
            <InputText
              v-model="form.secret"
              type="password"
              placeholder="签名密钥（不填则不使用签名验证）"
            />
          </div>

          <div class="flex items-center gap-4 md:col-span-2">
            <label class="inline-flex items-center gap-2 text-surface-700 dark:text-surface-200">
              <Checkbox v-model="form.is_active" binary />
              启用此通道
            </label>
            <label class="inline-flex items-center gap-2 text-surface-700 dark:text-surface-200">
              <Checkbox v-model="form.is_default" binary />
              设为默认通道
            </label>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <Button :label="saving ? '保存中...' : '保存通道'" :loading="saving" @click="submitForm">
            <template #icon><Save class="h-4 w-4" /></template>
          </Button>
          <Button outlined :disabled="saving" @click="closeDialog">取消</Button>
        </div>
      </div>
    </SimpleModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { PlusCircle, Pencil, Play, Trash2, Save } from 'lucide-vue-next'
import {
  createNotificationChannel,
  updateNotificationChannel,
  deleteNotificationChannel,
  testNotificationChannel,
} from '@/api/index'
import { channelIcons, channelTypeLabels } from '@/utils/channelIcons'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import SimpleModal from '@/components/ui/SimpleModal.vue'

const props = defineProps<{ channels: any[] }>()
const emit = defineEmits<{ refreshChannels: [] }>()

const baseLabels = channelTypeLabels
const MANAGED_CHANNEL_TYPES = ['dingtalk', 'feishu', 'wechat', 'slack', 'email']
const visibleChannels = computed(() => props.channels.filter(ch => ch.notification_type !== 'gitlab'))

const channelTypes = computed(() => {
  const typeSet = new Set<string>(MANAGED_CHANNEL_TYPES)
  visibleChannels.value.forEach(ch => typeSet.add(ch.notification_type))
  return Array.from(typeSet).map(value => ({ value, label: baseLabels[value] || value }))
})

const grouped = computed(() => {
  const map: Record<string, any[]> = {}
  channelTypes.value.forEach(item => { map[item.value] = [] })
  visibleChannels.value.forEach(ch => {
    if (!map[ch.notification_type]) map[ch.notification_type] = []
    map[ch.notification_type].push(ch)
  })
  return map
})

const dialogVisible = ref(false)
const saving = ref(false)
const testingId = ref<number | null>(null)

const emptyForm = () => ({
  id: null as number | null,
  name: '',
  notification_type: channelTypes.value[0]?.value || 'dingtalk',
  description: '',
  webhook_url: '',
  secret: '',
  is_active: true,
  is_default: false,
})

const form = ref(emptyForm())

const openDialog = (notificationType?: string) => {
  form.value = emptyForm()
  if (notificationType) form.value.notification_type = notificationType
  dialogVisible.value = true
}

const editChannel = (channel: any) => {
  form.value = {
    id: channel.id,
    name: channel.name,
    notification_type: channel.notification_type,
    description: channel.description || '',
    webhook_url: channel.webhook_url || '',
    secret: channel.secret || '',
    is_active: channel.is_active !== false,
    is_default: channel.is_default || false,
  }
  dialogVisible.value = true
}

const closeDialog = () => {
  dialogVisible.value = false
  form.value = emptyForm()
}

const submitForm = async () => {
  saving.value = true
  try {
    const payload: any = {
      name: form.value.name,
      notification_type: form.value.notification_type,
      description: form.value.description,
      is_active: form.value.is_active,
      is_default: form.value.is_default,
    }
    const configData: Record<string, any> = {}
    if (['dingtalk', 'feishu', 'slack', 'wechat'].includes(form.value.notification_type)) {
      configData.webhook_url = form.value.webhook_url
    }
    if (['dingtalk', 'feishu'].includes(form.value.notification_type)) {
      configData.secret = form.value.secret?.trim() || null
    }
    if (Object.keys(configData).length > 0) {
      payload.config_data = configData
    }

    if (form.value.id) {
      await updateNotificationChannel(form.value.id, payload)
    } else {
      await createNotificationChannel(payload)
    }
    dialogVisible.value = false
    form.value = emptyForm()
    emit('refreshChannels')
  } catch (error) {
    console.error('Failed to save notification channel:', error)
  } finally {
    saving.value = false
  }
}

const removeChannel = async (channel: any) => {
  if (!channel?.id) return
  const confirmed = window.confirm(`确认删除通道「${channel.name}」吗？`)
  if (!confirmed) return
  try {
    await deleteNotificationChannel(channel.id)
    emit('refreshChannels')
  } catch (error) {
    console.error('Failed to delete notification channel:', error)
  }
}

const testChannel = async (channel: any) => {
  if (!channel?.id) return
  testingId.value = channel.id
  try {
    await testNotificationChannel(channel.id)
  } catch (error) {
    console.error('Failed to test notification channel:', error)
  } finally {
    testingId.value = null
  }
}
</script>
