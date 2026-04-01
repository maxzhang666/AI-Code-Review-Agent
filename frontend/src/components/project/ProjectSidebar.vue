<template>
  <div class="space-y-6">
    <Card>
      <template #content>
        <div class="space-y-4">
          <h3 class="mb-4 text-xl font-semibold tracking-tight text-color">项目统计</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <GitCommit class="w-4 h-4" /><span>总提交数</span>
              </div>
              <span class="font-semibold text-surface-900 dark:text-surface-100">{{ project?.commits_count || 0 }}</span>
            </div>
            <div class="h-px bg-surface-200/60"></div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <GitPullRequest class="w-4 h-4" /><span>合并请求</span>
              </div>
              <span class="font-semibold text-surface-900 dark:text-surface-100">{{ project?.mr_count || 0 }}</span>
            </div>
            <div class="h-px bg-surface-200/60"></div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <CheckCircle2 class="w-4 h-4" /><span>审查完成</span>
              </div>
              <span class="font-semibold text-green-600 dark:text-green-300">{{ stats?.reviews?.completed || 0 }}</span>
            </div>
            <div class="h-px bg-surface-200/60"></div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <AlertCircle class="w-4 h-4" /><span>本周审查</span>
              </div>
              <span class="font-semibold text-orange-600 dark:text-orange-300">{{ stats?.reviews?.weekly || 0 }}</span>
            </div>
            <div class="h-px bg-surface-200/60"></div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-surface-600">
                <TrendingUp class="w-4 h-4" /><span>审查成功率</span>
              </div>
              <span class="font-semibold text-primary-600 dark:text-primary-300">{{ stats?.reviews?.completion_rate?.toFixed(1) || 0 }}%</span>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <h3 class="mb-4 text-xl font-semibold tracking-tight text-color">活跃贡献者</h3>
        <div class="space-y-3">
          <div
            v-for="(contributor, index) in contributors"
            :key="index"
            class="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-50 transition-colors duration-200 dark:hover:bg-surface-800/70"
          >
            <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary-600 flex items-center justify-center text-white text-xs font-semibold">
              {{ contributor.initials }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium text-surface-900 dark:text-surface-100">{{ contributor.name }}</div>
              <div class="text-2xs text-surface-500 dark:text-surface-400">{{ contributor.commits }} commits</div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="space-y-3">
          <Button severity="danger" v-if="project?.review_enabled" class="w-full" rounded label="关闭审查" :disabled="loading" @click="$emit('toggle-review')">
            <template #icon><Power class="w-4 h-4" /></template>
          </Button>
          <Button v-else class="w-full" rounded label="开启审查" :disabled="loading" @click="$emit('toggle-review')">
            <template #icon><Power class="w-4 h-4" /></template>
          </Button>
          <Button
            v-if="isIgnoreStrategyEnabled(project?.ignore_strategy_enabled)"
            severity="secondary"
            outlined
            class="w-full"
            rounded
            label="关闭忽略策略自动生效"
            :disabled="loading"
            @click="$emit('toggle-ignore-strategy')"
          >
            <template #icon><ShieldOff class="w-4 h-4" /></template>
          </Button>
          <Button
            v-else
            severity="secondary"
            class="w-full"
            rounded
            label="开启忽略策略自动生效"
            :disabled="loading"
            @click="$emit('toggle-ignore-strategy')"
          >
            <template #icon><ShieldCheck class="w-4 h-4" /></template>
          </Button>
          <Button outlined class="w-full" rounded label="查看 GitLab" @click="openUrl(project?.project_url)">
            <template #icon><ExternalLink class="w-4 h-4" /></template>
          </Button>
          <Button text class="w-full" rounded :label="loading ? '刷新中...' : '刷新数据'" :disabled="loading" @click="$emit('refresh')">
            <template #icon><Settings class="w-4 h-4" /></template>
          </Button>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import {
  GitCommit, GitPullRequest, CheckCircle2, AlertCircle,
  TrendingUp, Power, ExternalLink, Settings, ShieldCheck, ShieldOff
} from 'lucide-vue-next'
import Button from 'primevue/button'
import Card from 'primevue/card'

defineProps<{
  project: any
  stats: any
  contributors: any[]
  loading: boolean
}>()

defineEmits<{
  'toggle-review': []
  'toggle-ignore-strategy': []
  'refresh': []
}>()

const openUrl = (url?: string) => {
  if (url) window.open(url, '_blank')
}

const isIgnoreStrategyEnabled = (value: unknown): boolean => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (!normalized) return false
    if (['true', 'yes', 'on', 'enabled', 'enable', 'active', 'open'].includes(normalized)) return true
    if (['false', 'no', 'off', 'disabled', 'disable', 'inactive', 'close', 'closed'].includes(normalized)) return false
    const numeric = Number(normalized)
    if (!Number.isNaN(numeric)) return numeric !== 0
    return true
  }
  return false
}
</script>
