<template>
  <div class="flex items-center gap-3">
    <div class="h-2 w-2 rounded-full" :class="dotClass"></div>
    <h3 class="text-lg font-semibold text-surface-900 dark:text-surface-0">{{ title }}</h3>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    dotClass?: string
  }>(),
  {
    dotClass: 'bg-primary-500',
  }
)
</script>
