<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-2 h-2 bg-orange-500 rounded-full"></div>
            <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">通知设置</h3>
          </div>
          <Button rounded label="保存" :loading="saving" @click="save">
            <template #icon><Save class="w-4 h-4" /></template>
          </Button>
        </div>

        <div class="flex items-center justify-between bg-surface-50 border border-surface-200/60 rounded-lg px-3 py-2 dark:bg-surface-800/70 dark:border-surface-700/60">
          <span class="text-xs text-surface-700 dark:text-surface-200">GitLab 评论通知</span>
          <ToggleSwitch v-model="localGitlabComment" />
        </div>

        <div class="space-y-4">
          <div v-for="type in computedChannelTypes" :key="type.value" class="space-y-2">
            <div class="flex items-center gap-2 text-xs font-semibold text-surface-600 uppercase tracking-wide">
              <img v-if="channelIcons[type.value]" :src="channelIcons[type.value]" :alt="type.label" class="w-4 h-4 object-contain" />
              <span>{{ type.label }}</span>
            </div>
            <div v-if="grouped[type.value]?.length" class="space-y-2">
              <div
                v-for="channel in grouped[type.value]"
                :key="channel.id"
                class="flex items-center justify-between bg-surface-50 border border-surface-200/60 rounded-lg px-4 py-3 hover:bg-surface-100/50 transition-colors duration-200 dark:bg-surface-800/70 dark:border-surface-700/60 dark:hover:bg-surface-800"
              >
                <div class="flex items-start gap-2 flex-1 mr-3">
                  <img v-if="channelIcons[channel.notification_type]" :src="channelIcons[channel.notification_type]" :alt="channel.notification_type" class="w-5 h-5 mt-0.5 object-contain flex-shrink-0" />
                  <div class="flex-1">
                    <div class="text-surface-900 font-medium dark:text-surface-100">{{ channel.name }}</div>
                    <div class="text-xs text-surface-500 mt-0.5 dark:text-surface-400">{{ channel.description || '暂无备注' }}</div>
                  </div>
                </div>
                <ToggleSwitch
                  :model-value="localChannelIds.includes(Number(channel.id))"
                  @update:model-value="(value: boolean) => handleChannelSwitchChange(Number(channel.id), value)"
                />
              </div>
            </div>
            <div v-else class="text-xs text-surface-400 bg-surface-50 rounded-lg px-3 py-2 border border-dashed border-surface-200 dark:bg-surface-800/60 dark:border-surface-700 dark:text-surface-500">
              该类型暂无可用通道
            </div>
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Save } from 'lucide-vue-next'
import { updateProjectNotifications } from '@/api'
import { toast } from '@/utils/toast'
import { channelIcons, channelTypeLabels } from '@/utils/channelIcons'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ToggleSwitch from 'primevue/toggleswitch'

const props = defineProps<{
  projectId: string
  channels: any[]
  selectedChannelIds: number[]
  gitlabCommentEnabled: boolean
}>()

const emit = defineEmits<{
  saved: []
  'update:selectedChannelIds': [ids: number[]]
  'update:gitlabCommentEnabled': [val: boolean]
}>()

const localChannelIds = ref<number[]>([...props.selectedChannelIds])
const localGitlabComment = ref(props.gitlabCommentEnabled)
const saving = ref(false)

watch(() => props.selectedChannelIds, (ids) => { localChannelIds.value = [...ids] })
watch(() => props.gitlabCommentEnabled, (val) => { localGitlabComment.value = val })

const computedChannelTypes = computed(() => {
  const set = new Set(props.channels.map(item => item.notification_type))
  return Array.from(set).map(value => ({ value, label: channelTypeLabels[value] || value }))
})

const grouped = computed(() => {
  const map: Record<string, any[]> = {}
  computedChannelTypes.value.forEach(item => { map[item.value] = [] })
  props.channels.forEach(channel => {
    if (!map[channel.notification_type]) map[channel.notification_type] = []
    map[channel.notification_type].push(channel)
  })
  return map
})

const toggleChannel = (id: number, val: boolean) => {
  if (val) {
    if (!localChannelIds.value.includes(id)) localChannelIds.value.push(id)
  } else {
    localChannelIds.value = localChannelIds.value.filter(i => i !== id)
  }
}

const handleChannelSwitchChange = (id: number, value: string | number | boolean) => {
  toggleChannel(id, Boolean(value))
}

const save = async () => {
  saving.value = true
  try {
    const normalizedIds = Array.from(new Set(localChannelIds.value.map(id => Number(id)))).filter(id => !Number.isNaN(id))
    await updateProjectNotifications(props.projectId, {
      gitlab_comment_enabled: localGitlabComment.value,
      channel_ids: normalizedIds
    })
    toast.success('通知设置已更新')
    emit('update:selectedChannelIds', normalizedIds)
    emit('update:gitlabCommentEnabled', localGitlabComment.value)
    emit('saved')
  } catch (error) {
    console.error('Failed to save project notifications:', error)
    toast.error('保存通知设置失败')
  } finally {
    saving.value = false
  }
}
</script>
