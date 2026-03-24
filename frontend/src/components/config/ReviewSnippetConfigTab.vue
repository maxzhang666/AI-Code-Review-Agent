<template>
  <Card>
    <template #content>
      <div class="space-y-6">
        <ConfigSectionHeader title="问题代码行" dot-class="bg-cyan-500" />

        <div class="rounded-xl border border-cyan-200/60 bg-gradient-to-r from-cyan-50 to-sky-50 p-4 text-cyan-700 dark:border-cyan-500/35 dark:from-cyan-500/12 dark:to-sky-500/12 dark:text-cyan-200">
          <div class="mb-2 flex items-center gap-2 font-medium">
            <Code2 class="h-4 w-4" />
            问题代码行获取策略
          </div>
          <div class="space-y-1 text-xs text-cyan-700/90 dark:text-cyan-100/90">
            <div>1. 推荐使用“按行号计算优先”，基于 MR Diff 与行号生成精确问题代码行。</div>
            <div>2. 当行号无法定位时，系统会自动回退到大模型返回内容的首行。</div>
            <div>3. 保存后对后续新审查任务生效，历史记录不受影响。</div>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <button
            v-for="option in options"
            :key="option.value"
            type="button"
            class="rounded-xl border p-4 text-left transition-all duration-200"
            :class="source === option.value
              ? 'border-primary-400 bg-primary-50/70 shadow-sm dark:border-primary-400/70 dark:bg-primary-500/10'
              : 'border-surface-200/70 bg-surface-50/50 hover:border-surface-300 hover:bg-surface-100/60 dark:border-surface-700/70 dark:bg-surface-900 dark:hover:border-surface-600 dark:hover:bg-surface-800/70'"
            @click="emit('update:source', option.value)"
          >
            <div class="mb-2 flex items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <component :is="option.icon" class="h-4 w-4 text-surface-700 dark:text-surface-200" />
                <span class="text-sm font-semibold text-surface-900 dark:text-surface-0">{{ option.title }}</span>
              </div>
              <Tag
                v-if="option.recommended"
                severity="success"
                value="推荐"
                class="!text-[10px]"
              />
            </div>
            <p class="text-xs leading-5 text-surface-600 dark:text-surface-300">{{ option.description }}</p>
          </button>
        </div>

        <div class="rounded-lg border border-surface-200/70 bg-surface-50/70 px-3 py-2 text-xs text-surface-600 dark:border-surface-700/70 dark:bg-surface-900 dark:text-surface-300">
          当前生效策略：<span class="font-semibold text-surface-900 dark:text-surface-100">{{ currentSourceLabel }}</span>
        </div>

        <ConfigActionBar
          :saving="saving"
          :save-disabled="!dirty"
          @reset="emit('reset')"
          @save="emit('save')"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Code2, BrainCircuit } from 'lucide-vue-next'
import ConfigSectionHeader from '@/components/config/ConfigSectionHeader.vue'
import ConfigActionBar from '@/components/config/ConfigActionBar.vue'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

const props = withDefaults(
  defineProps<{
    source: 'line' | 'llm'
    saving?: boolean
    dirty?: boolean
  }>(),
  {
    saving: false,
    dirty: false,
  }
)

const emit = defineEmits<{
  'update:source': [value: 'line' | 'llm']
  save: []
  reset: []
}>()

const options: Array<{
  title: string
  description: string
  value: 'line' | 'llm'
  recommended: boolean
  icon: any
}> = [
  {
    title: '按行号计算优先',
    description: '优先按 file + line_start 从 MR Diff 计算精确代码行，更稳定且可追溯。',
    value: 'line',
    recommended: true,
    icon: Code2,
  },
  {
    title: '大模型返回优先',
    description: '优先使用模型返回的 code_snippet 首行，作为精确问题代码行。',
    value: 'llm',
    recommended: false,
    icon: BrainCircuit,
  },
]

const currentSourceLabel = computed(() => {
  return options.find((item) => item.value === props.source)?.title || '按行号计算优先'
})
</script>
