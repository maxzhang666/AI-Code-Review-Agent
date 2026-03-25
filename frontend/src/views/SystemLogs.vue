<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 class="text-xl font-semibold text-surface-800 dark:text-surface-100">系统日志</h2>
            <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">查看后端 logs 目录下的日志文件内容</p>
          </div>

          <div class="flex flex-wrap items-end gap-3">
            <div class="min-w-56">
              <label class="mb-1 block text-xs text-surface-500 dark:text-surface-400">日志文件</label>
              <Select
                v-model="selectedFile"
                :options="files"
                option-label="name"
                option-value="name"
                placeholder="选择日志文件"
                class="w-full"
                :loading="loadingFiles"
              />
            </div>

            <div class="w-36">
              <label class="mb-1 block text-xs text-surface-500 dark:text-surface-400">读取行数</label>
              <InputNumber v-model="lineCount" :min="1" :max="5000" show-buttons class="w-full" />
            </div>

            <Button label="刷新文件" outlined :loading="loadingFiles" @click="loadFiles(false)">
              <template #icon><RefreshCw class="h-4 w-4" /></template>
            </Button>

            <Button label="读取内容" :disabled="!selectedFile" :loading="loadingContent" @click="loadContent">
              <template #icon><FileText class="h-4 w-4" /></template>
            </Button>
          </div>
        </div>

        <div v-if="errorMessage" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/35 dark:bg-red-500/10 dark:text-red-300">
          {{ errorMessage }}
        </div>

        <div v-if="!files.length && !loadingFiles" class="rounded-xl border border-dashed border-surface-200 bg-surface-50 p-8 text-center text-surface-500 dark:border-surface-700 dark:bg-surface-800/60 dark:text-surface-400">
          暂无可用日志文件
        </div>

        <div v-else>
          <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
            <Tag v-if="selectedFile" severity="info">{{ selectedFile }}</Tag>
            <Tag severity="secondary">总行数: {{ totalLines }}</Tag>
            <Tag severity="secondary">返回行数: {{ returnedLines }}</Tag>
            <Tag v-if="truncated" severity="warn">已截断，仅显示末尾 {{ returnedLines }} 行</Tag>
            <Tag v-if="selectedFileMeta" severity="contrast">{{ formatSize(selectedFileMeta.size_bytes) }}</Tag>
            <Tag v-if="selectedFileMeta" severity="contrast">{{ formatTime(selectedFileMeta.modified_at) }}</Tag>
          </div>

          <div v-if="loadingContent" class="flex w-full justify-center py-10">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-surface-300 border-t-primary"></div>
          </div>

          <pre
            v-else
            class="max-h-[70vh] overflow-auto rounded-xl border border-surface-200 bg-surface-950 p-4 text-xs leading-relaxed text-surface-100 dark:border-surface-700"
          ><code>{{ content || '当前文件暂无内容' }}</code></pre>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RefreshCw, FileText } from 'lucide-vue-next'
import { getSystemLogFileContent, getSystemLogFiles } from '@/api/index'
import { formatBackendDateTime } from '@/utils/datetime'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

interface SystemLogFileItem {
  name: string
  size_bytes: number
  modified_at: string
}

const files = ref<SystemLogFileItem[]>([])
const selectedFile = ref<string>('')
const lineCount = ref<number>(300)
const content = ref<string>('')
const totalLines = ref<number>(0)
const returnedLines = ref<number>(0)
const truncated = ref<boolean>(false)
const loadingFiles = ref<boolean>(false)
const loadingContent = ref<boolean>(false)
const errorMessage = ref<string>('')

const selectedFileMeta = computed(() => files.value.find((item) => item.name === selectedFile.value))

const formatSize = (bytes: number) => {
  if (!Number.isFinite(bytes) || bytes < 0) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

const formatTime = (value: string) => formatBackendDateTime(value)

const loadFiles = async (preserveSelection: boolean = true) => {
  loadingFiles.value = true
  errorMessage.value = ''
  const previousSelection = selectedFile.value
  try {
    const response: any = await getSystemLogFiles()
    const nextFiles = Array.isArray(response?.results) ? response.results : []
    files.value = nextFiles

    if (!nextFiles.length) {
      selectedFile.value = ''
      content.value = ''
      totalLines.value = 0
      returnedLines.value = 0
      truncated.value = false
      return
    }

    if (
      preserveSelection &&
      selectedFile.value &&
      nextFiles.some((item: SystemLogFileItem) => item.name === selectedFile.value)
    ) {
      await loadContent()
      return
    }

    selectedFile.value = nextFiles[0].name
    if (selectedFile.value === previousSelection) {
      await loadContent()
    }
  } catch (error) {
    console.error('加载系统日志文件列表失败:', error)
    errorMessage.value = '加载日志文件列表失败'
  } finally {
    loadingFiles.value = false
  }
}

const loadContent = async () => {
  if (!selectedFile.value) return
  loadingContent.value = true
  errorMessage.value = ''
  try {
    const response: any = await getSystemLogFileContent(selectedFile.value, lineCount.value)
    content.value = String(response?.content || '')
    totalLines.value = Number(response?.total_lines || 0)
    returnedLines.value = Number(response?.returned_lines || 0)
    truncated.value = Boolean(response?.truncated)
  } catch (error) {
    console.error('加载系统日志文件内容失败:', error)
    content.value = ''
    totalLines.value = 0
    returnedLines.value = 0
    truncated.value = false
    errorMessage.value = '加载日志内容失败'
  } finally {
    loadingContent.value = false
  }
}

onMounted(async () => {
  await loadFiles()
})

watch(selectedFile, async (value, previousValue) => {
  if (!value || value === previousValue) return
  await loadContent()
})
</script>
