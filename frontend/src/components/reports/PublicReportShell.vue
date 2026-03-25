<template>
  <div class="public-report-shell relative min-h-screen overflow-hidden">
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute -left-28 -top-24 h-72 w-72 rounded-full bg-sky-400/20 blur-3xl" />
      <div class="absolute right-[-80px] top-12 h-80 w-80 rounded-full bg-cyan-300/25 blur-3xl" />
      <div class="absolute bottom-[-140px] left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-indigo-300/20 blur-3xl" />
    </div>

    <div class="relative mx-auto max-w-7xl px-4 py-8 md:px-8 md:py-12">
      <header class="rounded-2xl border border-surface-200/70 bg-white/85 p-5 backdrop-blur-xl shadow-[0_18px_45px_rgba(15,23,42,0.08)] dark:border-surface-700/60 dark:bg-surface-900/80">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-600">Code Review Weekly</p>
            <h1 class="mt-2 text-2xl font-semibold text-surface-900 dark:text-surface-0">{{ title }}</h1>
            <p class="mt-2 max-w-2xl text-sm text-surface-600 dark:text-surface-300">{{ description }}</p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <slot name="actions" />
          </div>
        </div>

        <nav class="mt-5 inline-flex rounded-xl bg-surface-100/80 p-1 dark:bg-surface-800/80">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            :class="isActive(item.path)
              ? 'bg-white text-surface-900 shadow-sm dark:bg-surface-700 dark:text-surface-0'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-300 dark:hover:text-surface-0'"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </header>

      <main class="mt-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  title: string
  description: string
}>()

const route = useRoute()

const navItems = [
  { label: '成员周报', path: '/weekly-report/members' },
  { label: '团队周报', path: '/weekly-report/team' }
]

const isActive = (path: string) => route.path.startsWith(path)
</script>

<style scoped>
.public-report-shell {
  font-family:
    "IBM Plex Sans",
    "Avenir Next",
    "PingFang SC",
    "Hiragino Sans GB",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    sans-serif;
  background:
    radial-gradient(1400px 480px at 15% -10%, rgba(56, 189, 248, 0.22), transparent 60%),
    radial-gradient(1000px 400px at 95% 0%, rgba(45, 212, 191, 0.2), transparent 62%),
    linear-gradient(180deg, #eff8ff 0%, #f8fafc 45%, #f9fafb 100%);
}

:global(.dark) .public-report-shell {
  background:
    radial-gradient(1200px 420px at 10% -10%, rgba(56, 189, 248, 0.16), transparent 62%),
    radial-gradient(900px 360px at 90% 0%, rgba(45, 212, 191, 0.16), transparent 62%),
    linear-gradient(180deg, #0b1020 0%, #0f172a 42%, #0b1220 100%);
}
</style>

