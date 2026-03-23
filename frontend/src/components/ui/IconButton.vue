<template>
  <button
    v-bind="$attrs"
    :type="type"
    :disabled="disabled"
    :class="[
      'inline-flex shrink-0 items-center justify-center rounded-full bg-transparent p-0 transition-colors duration-150',
      'focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-primary',
      'text-surface-500 hover:text-surface-800 dark:text-surface-300 dark:hover:text-surface-0',
      disabled ? 'cursor-not-allowed opacity-45' : 'cursor-pointer',
      sizeClass
    ]"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'small',
  disabled: false,
  type: 'button',
})

const sizeClass = computed(() => {
  if (props.size === 'large') return 'h-10 w-10'
  if (props.size === 'medium') return 'h-9 w-9'
  return 'h-8 w-8'
})
</script>
