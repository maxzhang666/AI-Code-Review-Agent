<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[120] flex items-center justify-center p-4"
      @click="handleMaskClick"
    >
      <div class="absolute inset-0 bg-slate-900/45 backdrop-blur-[1px]"></div>
      <div
        class="relative w-full overflow-hidden rounded-2xl border border-surface-200/60 bg-white shadow-2xl dark:border-surface-700/60 dark:bg-surface-900"
        :style="panelStyle"
        @click.stop
      >
        <div class="flex items-center justify-between border-b border-surface-200/60 px-5 py-4 dark:border-surface-700/60">
          <h3 class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ title }}</h3>
          <IconButton
            size="small"
            aria-label="关闭"
            @click="close"
          >
            <X class="h-4 w-4" />
          </IconButton>
        </div>
        <div class="max-h-[75vh] overflow-auto p-5">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from 'lucide-vue-next'
import IconButton from '@/components/ui/IconButton.vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  width?: number | string
  maskClosable?: boolean
}>(), {
  title: '',
  width: 640,
  maskClosable: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  close: []
}>()

const panelStyle = computed(() => {
  if (typeof props.width === 'number') {
    return { maxWidth: `${props.width}px` }
  }
  return { maxWidth: props.width }
})

const close = () => {
  emit('update:modelValue', false)
  emit('close')
}

const handleMaskClick = () => {
  if (!props.maskClosable) return
  close()
}
</script>
