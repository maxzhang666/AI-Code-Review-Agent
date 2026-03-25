<template>
  <div class="relative min-h-screen overflow-hidden bg-[radial-gradient(42rem_28rem_at_12%_0%,rgba(125,184,255,0.35),transparent_72%),radial-gradient(36rem_24rem_at_96%_100%,rgba(122,240,255,0.3),transparent_70%),#eff5ff] dark:bg-[radial-gradient(42rem_28rem_at_12%_0%,rgba(52,94,166,0.35),transparent_72%),radial-gradient(36rem_24rem_at_96%_100%,rgba(52,142,171,0.25),transparent_70%),#0c1526]">
    <div class="pointer-events-none absolute -top-20 left-1/4 h-52 w-52 rounded-full bg-primary-200/60 blur-3xl dark:bg-primary-600/20"></div>
    <div class="pointer-events-none absolute -bottom-20 right-0 h-60 w-60 rounded-full bg-cyan-200/60 blur-3xl dark:bg-cyan-500/20"></div>

    <main class="relative mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-8 sm:px-6 sm:py-12">
      <section class="w-full rounded-3xl border border-white/90 bg-surface-0/85 p-4 shadow-[0_28px_56px_rgba(23,58,111,0.16)] backdrop-blur-sm dark:border-surface-700/70 dark:bg-surface-900/80 sm:p-6 lg:p-8">
        <article class="rounded-2xl border border-primary-100/80 bg-[linear-gradient(120deg,#eff6ff,#f4ffff)] p-5 dark:border-primary-700/60 dark:bg-[linear-gradient(120deg,rgba(30,58,138,0.36),rgba(8,47,73,0.36))] sm:p-6">
          <div class="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p class="inline-flex items-center gap-2 rounded-full border border-primary-200/90 bg-white/80 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.14em] text-primary-700 dark:border-primary-500/50 dark:bg-primary-500/10 dark:text-primary-200">
                <ShieldCheck class="h-3.5 w-3.5" />
                Code Review Agent
              </p>
              <h1 class="mt-4 text-3xl font-semibold tracking-tight text-surface-900 dark:text-surface-0 sm:text-4xl">
                统一安全登录入口
              </h1>
              <p class="mt-3 max-w-3xl text-sm leading-6 text-surface-600 dark:text-surface-300">
                登录后可访问代码审查、项目配置与系统管理功能。
              </p>
            </div>
            <div class="flex flex-wrap gap-2 md:justify-end">
              <span class="rounded-full border border-primary-200/90 bg-white/80 px-3 py-1 text-xs text-primary-700 dark:border-primary-500/45 dark:bg-primary-500/10 dark:text-primary-200">代码审查</span>
              <span class="rounded-full border border-primary-200/90 bg-white/80 px-3 py-1 text-xs text-primary-700 dark:border-primary-500/45 dark:bg-primary-500/10 dark:text-primary-200">项目配置</span>
              <span class="rounded-full border border-primary-200/90 bg-white/80 px-3 py-1 text-xs text-primary-700 dark:border-primary-500/45 dark:bg-primary-500/10 dark:text-primary-200">权限管理</span>
              <span class="rounded-full border border-primary-200/90 bg-white/80 px-3 py-1 text-xs text-primary-700 dark:border-primary-500/45 dark:bg-primary-500/10 dark:text-primary-200">操作审计</span>
            </div>
          </div>
        </article>

        <article class="mt-5 grid gap-5 xl:grid-cols-[1fr_420px]">
          <section class="rounded-2xl border border-primary-100/80 bg-surface-0 p-5 dark:border-primary-700/50 dark:bg-surface-900/70 sm:p-6">
            <h2 class="text-lg font-semibold text-surface-900 dark:text-surface-0">登录说明</h2>
            <p class="mt-2 text-sm leading-6 text-surface-600 dark:text-surface-300">请使用已授权账号登录。</p>
            <div class="mt-5 grid gap-3 sm:grid-cols-2">
              <div class="rounded-xl border border-primary-100/80 bg-primary-50/45 p-4 dark:border-primary-600/35 dark:bg-primary-500/10">
                <p class="text-sm font-semibold text-primary-700 dark:text-primary-200">安全范围</p>
                <p class="mt-1 text-xs leading-5 text-surface-600 dark:text-surface-300">审查记录与配置数据受保护。</p>
              </div>
              <div class="rounded-xl border border-primary-100/80 bg-primary-50/45 p-4 dark:border-primary-600/35 dark:bg-primary-500/10">
                <p class="text-sm font-semibold text-primary-700 dark:text-primary-200">访问控制</p>
                <p class="mt-1 text-xs leading-5 text-surface-600 dark:text-surface-300">按角色分配可访问的功能。</p>
              </div>
              <div class="rounded-xl border border-primary-100/80 bg-primary-50/45 p-4 dark:border-primary-600/35 dark:bg-primary-500/10">
                <p class="text-sm font-semibold text-primary-700 dark:text-primary-200">会话保护</p>
                <p class="mt-1 text-xs leading-5 text-surface-600 dark:text-surface-300">异常会话将要求重新登录。</p>
              </div>
              <div class="rounded-xl border border-primary-100/80 bg-primary-50/45 p-4 dark:border-primary-600/35 dark:bg-primary-500/10">
                <p class="text-sm font-semibold text-primary-700 dark:text-primary-200">审计追踪</p>
                <p class="mt-1 text-xs leading-5 text-surface-600 dark:text-surface-300">关键操作全量记录，便于追溯。</p>
              </div>
            </div>
          </section>

          <section class="rounded-2xl border border-primary-100/80 bg-[linear-gradient(180deg,#ffffff,#f4f9ff)] p-6 dark:border-primary-700/50 dark:bg-[linear-gradient(180deg,rgba(24,24,27,0.92),rgba(9,9,11,0.96))] sm:p-7">
            <div class="mb-6 space-y-2">
              <h2 class="text-2xl font-semibold tracking-tight text-surface-900 dark:text-surface-0">账号登录</h2>
              <p class="text-sm text-surface-500 dark:text-surface-400">请输入账号和密码以继续访问后台系统。</p>
            </div>

            <form class="space-y-5" @submit.prevent="handleSubmit">
              <div class="space-y-2">
                <label class="text-xs font-medium uppercase tracking-wide text-surface-500 dark:text-surface-400">账号</label>
                <IconField class="w-full">
                  <InputIcon class="text-surface-400">
                    <User class="h-4 w-4" />
                  </InputIcon>
                  <InputText
                    v-model="username"
                    autocomplete="username"
                    placeholder="请输入账号"
                    class="w-full"
                    :disabled="isSubmitting"
                  />
                </IconField>
              </div>

              <div class="space-y-2">
                <label class="text-xs font-medium uppercase tracking-wide text-surface-500 dark:text-surface-400">密码</label>
                <div class="relative">
                  <IconField class="w-full">
                    <InputIcon class="text-surface-400">
                      <LockKeyhole class="h-4 w-4" />
                    </InputIcon>
                    <InputText
                      v-model="password"
                      :type="showPassword ? 'text' : 'password'"
                      autocomplete="current-password"
                      placeholder="请输入密码"
                      class="w-full pr-11"
                      :disabled="isSubmitting"
                    />
                  </IconField>
                  <button
                    type="button"
                    class="absolute right-2 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-surface-500 leading-none transition-colors hover:bg-surface-100 hover:text-surface-900 dark:hover:bg-surface-800 dark:hover:text-surface-100"
                    :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                    @click="showPassword = !showPassword"
                  >
                    <span class="relative block h-4 w-4">
                      <EyeOff v-if="showPassword" class="absolute inset-0 h-4 w-4" />
                      <Eye v-else class="absolute inset-0 h-4 w-4" />
                    </span>
                  </button>
                </div>
              </div>

              <div class="flex items-center justify-between text-sm">
                <label class="inline-flex cursor-pointer items-center gap-2 text-surface-600 dark:text-surface-300">
                  <Checkbox v-model="rememberMe" binary :disabled="isSubmitting" />
                  记住我
                </label>
                <span class="text-xs text-surface-500">登录后继续访问</span>
              </div>

              <div class="min-h-11">
                <p v-if="errorMessage" class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-300">
                  {{ errorMessage }}
                </p>
              </div>

              <Button type="submit" :loading="isSubmitting" class="w-full">
                登录
              </Button>
            </form>
          </section>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, LockKeyhole, ShieldCheck, User } from 'lucide-vue-next'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const rememberMe = ref(true)
const showPassword = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')

const resolveRedirectPath = (): string => {
  const raw = route.query.redirect
  if (typeof raw !== 'string') return '/dashboard'
  if (!raw.startsWith('/')) return '/dashboard'
  if (raw.startsWith('//')) return '/dashboard'
  return raw
}

const handleSubmit = async () => {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const result = await auth.login({
      username: username.value,
      password: password.value,
      remember: rememberMe.value
    })
    if (!result.ok) {
      errorMessage.value = result.message || '登录失败'
      return
    }
    await router.replace(resolveRedirectPath())
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
:deep(.p-inputtext) {
  transition-property: border-color, box-shadow, background-color, color;
}

:deep(.p-button),
:deep(.p-checkbox-box) {
  transition-property: border-color, box-shadow, background-color, color;
}
</style>
