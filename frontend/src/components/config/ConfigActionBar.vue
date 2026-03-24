<template>
  <div class="flex items-center justify-end gap-3 border-t border-surface-200/50 pt-4">
    <Button
      severity="secondary"
      outlined
      :disabled="resetDisabled || saving"
      @click="$emit('reset')"
    >
      {{ resetLabel }}
    </Button>
    <Button
      :loading="saving"
      :disabled="saveDisabled"
      @click="$emit('save')"
    >
      {{ saving ? savingLabel : saveLabel }}
    </Button>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'

withDefaults(
  defineProps<{
    saving?: boolean
    saveDisabled?: boolean
    resetDisabled?: boolean
    saveLabel?: string
    savingLabel?: string
    resetLabel?: string
  }>(),
  {
    saving: false,
    saveDisabled: false,
    resetDisabled: false,
    saveLabel: '保存配置',
    savingLabel: '保存中...',
    resetLabel: '重置',
  }
)

defineEmits<{
  save: []
  reset: []
}>()
</script>
