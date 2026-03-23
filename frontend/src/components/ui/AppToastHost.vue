<template>
  <Toast group="app" position="top-right" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Toast from 'primevue/toast'
import { setToastHandler, type ToastPayload } from '@/utils/toast'

const primeToast = useToast()

const severityMap: Record<ToastPayload['type'], 'success' | 'info' | 'warn' | 'error'> = {
  success: 'success',
  info: 'info',
  warning: 'warn',
  error: 'error',
}

const summaryMap: Record<ToastPayload['type'], string> = {
  success: '成功',
  info: '提示',
  warning: '警告',
  error: '错误',
}

const handler = (payload: ToastPayload) => {
  primeToast.add({
    group: 'app',
    severity: severityMap[payload.type],
    summary: summaryMap[payload.type],
    detail: payload.message,
    life: payload.duration ?? 3000,
  })
}

onMounted(() => {
  setToastHandler(handler)
})

onBeforeUnmount(() => {
  setToastHandler(null)
})
</script>
