<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <div class="flex items-center gap-3">
          <div class="h-2 w-2 rounded-full bg-purple-500"></div>
          <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-100">Claude CLI 配置</h3>
        </div>

        <div class="rounded-xl border border-surface-200/40 bg-surface-50/50 p-4 text-surface-600 dark:border-surface-700/50 dark:bg-surface-800/60 dark:text-surface-300">
          配置 Claude CLI 运行所需的环境变量。这些配置会在执行代码审查时注入运行环境。
        </div>

        <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div class="space-y-1 md:col-span-2">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">ANTHROPIC_BASE_URL</label>
            <InputText
              :model-value="config.anthropic_base_url"
              placeholder="https://api.anthropic.com"
              @update:model-value="update('anthropic_base_url', String($event || ''))"
            />
            <p class="text-xs text-surface-500">Claude API 的基础地址，留空使用默认值</p>
          </div>

          <div class="space-y-1 md:col-span-2">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">ANTHROPIC_AUTH_TOKEN</label>
            <InputText
              :model-value="config.anthropic_auth_token"
              type="password"
              placeholder="请输入 Claude 认证令牌"
              @update:model-value="update('anthropic_auth_token', String($event || ''))"
            />
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">CLI 路径</label>
            <InputText
              :model-value="config.cli_path"
              placeholder="claude"
              @update:model-value="update('cli_path', String($event || ''))"
            />
            <p class="text-xs text-surface-500">Claude CLI 可执行文件路径</p>
          </div>

          <div class="space-y-1">
            <label class="text-xs font-medium uppercase tracking-wide text-surface-500">超时时间（秒）</label>
            <InputText
              :model-value="String(config.timeout)"
              type="number"
              @update:model-value="updateTimeout(String($event || ''))"
            />
          </div>
        </div>

        <div class="border-t border-surface-200/50 pt-6 dark:border-surface-700/60">
          <Button :loading="testing" :label="testing ? '测试中...' : '测试 Claude CLI 连接'" @click="$emit('test')">
            <template #icon><Play class="h-4 w-4" /></template>
          </Button>
          <p class="mt-2 text-xs text-surface-500 dark:text-surface-400">点击测试按钮验证 Claude CLI 是否正确安装并可连接。</p>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { Play } from 'lucide-vue-next'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'

const props = defineProps<{
  config: {
    anthropic_base_url: string
    anthropic_auth_token: string
    cli_path: string
    timeout: number
  }
  testing: boolean
}>()

const emit = defineEmits<{
  'update:config': [val: typeof props.config]
  test: []
}>()

const update = (key: string, val: string) => {
  emit('update:config', { ...props.config, [key]: val })
}

const updateTimeout = (value: string) => {
  const parsed = Number(value)
  emit('update:config', {
    ...props.config,
    timeout: Number.isFinite(parsed) ? parsed : props.config.timeout,
  })
}
</script>
