<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="审查提示词配置" dot-class="bg-indigo-500" />

        <div class="rounded-xl border border-indigo-200/60 bg-gradient-to-r from-indigo-50 to-purple-50 p-4 text-indigo-700 dark:border-indigo-500/35 dark:from-indigo-500/12 dark:to-purple-500/12 dark:text-indigo-200">
          <div class="mb-2 font-medium">为每个 Webhook 事件类型配置额外审查要求</div>
          <div class="space-y-1 text-xs">
            <div>* 此处内容会追加到系统提示词末尾，不会替换系统提示词</div>
            <div>* 可用于补充项目规范、重点风险点和审查偏好</div>
            <div>* 支持变量占位符：{project_name}, {author}, {title}, {source_branch} 等</div>
            <div>* 关闭开关或留空时，仅使用系统提示词</div>
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
                <span class="text-xs text-surface-500 dark:text-surface-400">启用额外要求</span>
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
                placeholder="请输入额外审查要求（将追加到系统提示词之后），支持 Markdown 格式和变量占位符...

示例：
在系统默认审查标准基础上，请额外关注以下要求：
1. 严格检查 SQL 注入与鉴权绕过风险
2. 对核心链路代码给出性能风险与复杂度建议
3. 优先按团队规范给出可直接落地的修改建议"
                class="min-h-[180px] w-full font-mono text-sm"
              />
              <div class="flex flex-col gap-3 rounded-lg bg-surface-50 px-3 py-2.5 dark:bg-surface-800/60 md:flex-row md:items-center md:justify-between">
                <div class="min-w-0 text-xs leading-5 text-surface-500 dark:text-surface-400">
                  该内容会作为“附加要求”拼接到系统提示词后。支持占位符：{project_name}, {author}, {title}, {description}, {source_branch}, {target_branch}, {mr_iid}, {file_count}, {changes_count}
                </div>
                <Button rounded size="small" label="保存" :loading="saving" class="self-end md:self-auto" @click="savePrompt(promptConfig)">
                  <template #icon><Save class="w-4 h-4" /></template>
                </Button>
              </div>
            </div>
            <div v-else class="rounded-lg bg-surface-50 px-3 py-2 text-xs italic text-surface-500 dark:bg-surface-800/60 dark:text-surface-400">
              当前仅使用系统提示词（无额外补充要求）
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
