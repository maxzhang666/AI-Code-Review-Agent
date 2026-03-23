<template>
  <div class="relative min-h-screen overflow-hidden bg-surface-50 dark:bg-surface-950">
    <div class="pointer-events-none absolute -top-32 -left-24 h-80 w-80 rounded-full bg-primary-200/60 blur-3xl dark:bg-primary-500/15"></div>
    <div class="pointer-events-none absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-cyan-200/70 blur-3xl dark:bg-cyan-500/20"></div>

    <main class="relative mx-auto flex min-h-screen w-full max-w-6xl items-center px-6 py-12">
      <section class="grid w-full items-stretch gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <article class="hidden rounded-3xl border border-surface-200/60 bg-white/65 p-10 shadow-xl backdrop-blur-lg lg:flex lg:flex-col lg:justify-between dark:border-surface-700/70 dark:bg-surface-900/65">
          <div>
            <p class="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50/85 px-3 py-1 text-xs font-medium text-primary-700 dark:border-primary-600/60 dark:bg-primary-500/10 dark:text-primary-300">
              <ShieldCheck class="h-3.5 w-3.5" />
              Secure Access Portal
            </p>
            <h1 class="mt-5 text-4xl font-semibold leading-tight tracking-tight text-surface-900 dark:text-surface-0">
              Code Review Agent
              <span class="block text-primary-600 dark:text-primary-300">统一安全登录</span>
            </h1>
            <p class="mt-4 max-w-xl text-sm leading-6 text-surface-600 dark:text-surface-300">
              为保护代码审查数据和配置安全，请先完成账号登录后再访问功能模块。
            </p>
          </div>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div class="rounded-xl border border-surface-200/70 bg-white/80 p-4 dark:border-surface-700/70 dark:bg-surface-900/80">
              <p class="text-xs uppercase tracking-wide text-surface-500">安全范围</p>
              <p class="mt-1 font-medium text-surface-900 dark:text-surface-100">审查与配置数据</p>
            </div>
            <div class="rounded-xl border border-surface-200/70 bg-white/80 p-4 dark:border-surface-700/70 dark:bg-surface-900/80">
              <p class="text-xs uppercase tracking-wide text-surface-500">鉴权策略</p>
              <p class="mt-1 font-medium text-surface-900 dark:text-surface-100">账号权限控制</p>
            </div>
          </div>
        </article>

        <article class="mx-auto w-full max-w-md rounded-3xl border border-surface-200/60 bg-white/85 p-7 shadow-xl backdrop-blur-lg dark:border-surface-700/70 dark:bg-surface-900/80 sm:p-8">
          <div class="mb-6 space-y-2">
            <h2 class="text-2xl font-semibold tracking-tight text-surface-900 dark:text-surface-0">账号登录</h2>
            <p class="text-sm text-surface-500 dark:text-surface-400">请输入账号和密码以继续访问后台系统。</p>
          </div>

          <form class="space-y-5" @submit.prevent="handleSubmit">
            <div class="space-y-2">
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">账号</label>
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
              <label class="text-xs font-medium uppercase tracking-wide text-surface-500">密码</label>
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
                  class="absolute right-2 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-surface-500 transition-colors hover:bg-surface-100 hover:text-surface-900 dark:hover:bg-surface-800 dark:hover:text-surface-100"
                  :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                  @click="showPassword = !showPassword"
                >
                  <EyeOff v-if="showPassword" class="h-4 w-4" />
                  <Eye v-else class="h-4 w-4" />
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

            <p v-if="errorMessage" class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-300">
              {{ errorMessage }}
            </p>

            <Button type="submit" :loading="isSubmitting" class="w-full">
              登录
            </Button>
          </form>
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
