<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="GitLab 配置" dot-class="bg-orange-500" />

        <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div class="md:col-span-2 space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">GitLab URL</label>
            <InputText
              :model-value="config.serverUrl"
              placeholder="https://gitlab.com"
              class="w-full"
              @update:model-value="update('serverUrl', String($event || ''))"
            />
          </div>

          <div class="md:col-span-2 space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">Access Token</label>
            <InputText
              :model-value="config.privateToken"
              type="password"
              placeholder="GitLab Access Token"
              class="w-full"
              @update:model-value="update('privateToken', String($event || ''))"
            />
          </div>

          <div class="md:col-span-2 space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">Site URL</label>
            <InputText
              :model-value="config.siteUrl"
              placeholder="https://review.example.com"
              class="w-full"
              @update:model-value="update('siteUrl', String($event || ''))"
            />
            <span class="text-xs text-surface-500">用于自动注册 Webhook 的外部访问地址（如 https://review.example.com）</span>
          </div>
        </div>

        <div class="space-y-4 border-t border-surface-200/50 pt-6">
          <ConfigSectionHeader title="Webhook 配置" dot-class="bg-purple-500" />

          <div class="rounded-xl border border-purple-200/60 bg-gradient-to-r from-purple-50 to-indigo-50 p-4 text-purple-700 dark:border-purple-500/35 dark:from-purple-500/12 dark:to-indigo-500/12 dark:text-purple-200">
            <div class="mb-2 font-medium">📌 配置 GitLab Webhook</div>
            <div class="space-y-1 text-xs text-purple-600">
              <div>1. 在 GitLab 项目中进入 Settings → Webhooks</div>
              <div>2. 将下方地址复制到 URL 字段</div>
              <div>3. 选择需要的触发事件并保存</div>
              <div>4. 点击 Add webhook 完成配置</div>
              <div v-if="!config.siteUrl">5. 将 {host} 和 {port} 替换为实际的域名和端口</div>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex items-center gap-2 rounded-xl border-2 border-primary-300 bg-gradient-to-r from-primary-50 to-indigo-50 px-3 py-2.5 dark:border-primary-500/40 dark:from-primary-500/12 dark:to-indigo-500/12">
              <div class="flex min-w-0 flex-1 items-center gap-2">
                <Link class="h-4 w-4 shrink-0 text-primary-600" />
                <span class="shrink-0 text-xs font-semibold text-primary-700">Webhook 地址:</span>
                <code class="flex-1 truncate rounded border border-primary-200 bg-white px-2 py-1 font-mono text-xs text-primary-700 dark:border-primary-500/35 dark:bg-surface-900 dark:text-primary-300">
                  {{ computedWebhookUrl }}
                </code>
              </div>
              <IconButton size="small" aria-label="复制 Webhook 地址" @click="copyWebhookUrl">
                <Copy class="h-4 w-4" />
              </IconButton>
            </div>
          </div>
        </div>

        <ConfigActionBar
          :saving="saving"
          @reset="$emit('reset')"
          @save="$emit('save')"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Copy, Link } from 'lucide-vue-next'
import IconButton from '@/components/ui/IconButton.vue'
import ConfigSectionHeader from '@/components/config/ConfigSectionHeader.vue'
import ConfigActionBar from '@/components/config/ConfigActionBar.vue'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'

const props = defineProps<{
  config: { serverUrl: string; privateToken: string; siteUrl: string }
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:config': [val: typeof props.config]
  save: []
  reset: []
}>()

const computedWebhookUrl = computed(() => {
  if (props.config.siteUrl) {
    return `${props.config.siteUrl.replace(/\/+$/, '')}/api/webhook/gitlab/`
  }
  return 'http://{host}:{port}/api/webhook/gitlab/'
})

const update = (key: string, val: string) => {
  emit('update:config', { ...props.config, [key]: val })
}

const copyWebhookUrl = async () => {
  try {
    await navigator.clipboard.writeText(computedWebhookUrl.value)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}
</script>
