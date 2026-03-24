<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="审查提示词配置" dot-class="bg-indigo-500" />

        <div class="rounded-xl border border-indigo-200/60 bg-gradient-to-r from-indigo-50 to-purple-50 p-4 text-indigo-700 dark:border-indigo-500/35 dark:from-indigo-500/12 dark:to-purple-500/12 dark:text-indigo-200">
          <div class="mb-2 font-medium">为每个 Webhook 事件类型自定义代码审查的提示词</div>
          <div class="space-y-1 text-xs">
            <div>* 让 AI 更符合项目特点进行审查</div>
            <div>* 支持变量占位符：{project_name}, {author}, {title}, {source_branch} 等</div>
            <div>* 留空则使用系统默认提示词</div>
          </div>
        </div>

        <div v-if="prompts.length === 0" class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-6 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/60 dark:text-surface-400">
          暂无配置，请先在 Webhook 事件页面启用事件。
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="promptConfig in prompts"
            :key="promptConfig.event_rule"
            class="rounded-xl border border-surface-200/60 bg-white p-5 transition-shadow duration-200 hover:shadow-md dark:border-surface-700/60 dark:bg-surface-900"
          >
            <div class="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex flex-wrap items-center gap-2">
                  <div class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ promptConfig.event_rule_name }}</div>
                  <Tag severity="info">{{ promptConfig.event_rule_type }}</Tag>
                </div>
                <div class="text-xs text-surface-500 dark:text-surface-400">{{ promptConfig.event_rule_description || '暂无描述' }}</div>
              </div>
              <div class="flex items-center gap-2 self-start rounded-lg border border-surface-200/70 bg-surface-50 px-2.5 py-1.5 dark:border-surface-700/70 dark:bg-surface-800/70">
                <span class="text-xs text-surface-500 dark:text-surface-400">自定义提示词</span>
                <ToggleSwitch
                  :model-value="Boolean(promptConfig.use_custom)"
                  @update:model-value="(value: boolean) => { promptConfig.use_custom = value; savePrompt(promptConfig) }"
                />
              </div>
            </div>

            <div v-if="promptConfig.use_custom" class="space-y-2">
              <Textarea
                v-model="promptConfig.custom_prompt"
                rows="10"
                placeholder="请输入自定义的审查提示词，支持 Markdown 格式和变量占位符...

示例：
请对项目 {project_name} 的 MR #{mr_iid} 进行代码审查。
作者：{author}
标题：{title}
分支：{source_branch} -> {target_branch}

请重点关注：
1. 代码安全性
2. 性能优化
3. 最佳实践"
                class="min-h-[180px] w-full font-mono text-sm"
              />
              <div class="flex flex-col gap-3 rounded-lg bg-surface-50 px-3 py-2.5 dark:bg-surface-800/60 md:flex-row md:items-center md:justify-between">
                <div class="min-w-0 text-xs leading-5 text-surface-500 dark:text-surface-400">
                  支持的占位符：{project_name}, {author}, {title}, {description}, {source_branch}, {target_branch}, {mr_iid}, {file_count}, {changes_count}
                </div>
                <Button rounded size="small" label="保存" :loading="saving" class="self-end md:self-auto" @click="savePrompt(promptConfig)">
                  <template #icon><Save class="w-4 h-4" /></template>
                </Button>
              </div>
            </div>
            <div v-else class="rounded-lg bg-surface-50 px-3 py-2 text-xs italic text-surface-500 dark:bg-surface-800/60 dark:text-surface-400">
              当前使用系统默认提示词
            </div>
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Save } from 'lucide-vue-next'
import { updateProjectWebhookEventPrompt } from '@/api'
import { toast } from '@/utils/toast'
import ConfigSectionHeader from '@/components/config/ConfigSectionHeader.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

const props = defineProps<{
  projectId: string
  prompts: any[]
}>()

const emit = defineEmits<{ saved: [] }>()
const saving = ref(false)

const savePrompt = async (promptConfig: any) => {
  saving.value = true
  try {
    await updateProjectWebhookEventPrompt(props.projectId, {
      event_rule_id: promptConfig.event_rule,
      custom_prompt: promptConfig.custom_prompt,
      use_custom: promptConfig.use_custom
    })
    toast.success('提示词配置已保存')
    emit('saved')
  } catch (error) {
    console.error('Failed to save prompt config:', error)
    toast.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>
