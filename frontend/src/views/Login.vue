<template>
  <div class="login-page">
    <main class="layout">
      <section class="hero">
        <h1>Code Review<br />管理平台</h1>
        <p>统一管理项目接入、自动化代码审查与问题治理流程，覆盖审查记录、Issue 工作台、周报与系统配置，帮助团队稳定提升交付质量。</p>
        <div class="hero-grid">
          <div class="hero-cell">项目管理</div>
          <div class="hero-cell">审查记录</div>
          <div class="hero-cell">问题分析</div>
          <div class="hero-cell">Issue 工作台</div>
          <div class="hero-cell">配置管理</div>
          <div class="hero-cell">系统日志</div>
        </div>
      </section>

      <section class="login-panel">
        <span class="tag">secure access</span>
        <h2>账号登录</h2>

        <form class="form-stack" @submit.prevent="handleSubmit">
          <div>
            <label class="field-label">账号</label>
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

          <div>
            <label class="field-label">密码</label>
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
                class="password-eye"
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

          <div class="form-row">
            <label class="remember-label">
              <Checkbox v-model="rememberMe" binary :disabled="isSubmitting" />
              记住我
            </label>
            <span>登录后继续访问</span>
          </div>

          <div class="error-slot">
            <p v-if="errorMessage" class="hint">
              {{ errorMessage }}
            </p>
          </div>

          <Button type="submit" :loading="isSubmitting" class="login-btn w-full">
            登录
          </Button>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, LockKeyhole, User } from 'lucide-vue-next'
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
.login-page {
  --ink: #0d1f38;
  --paper: #f9fcff;
  --line: #bed3f8;
  --muted: #526787;
  box-sizing: border-box;
  min-height: 100dvh;
  padding: 20px;
  background: linear-gradient(118deg, #f3f8ff 0%, #f3f8ff 54%, #dcecff 54%, #dcecff 100%);
  color: var(--ink);
  font-family: 'Plus Jakarta Sans', 'PingFang SC', 'Segoe UI', sans-serif;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
}

.login-page::before,
.login-page::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  filter: blur(44px);
  pointer-events: none;
}

.login-page::before {
  width: 340px;
  height: 340px;
  left: -120px;
  top: -90px;
  background: #5a9bff88;
}

.login-page::after {
  width: 300px;
  height: 300px;
  right: -90px;
  bottom: -70px;
  background: #53d3ff88;
}

.layout {
  position: relative;
  z-index: 1;
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 430px);
  gap: clamp(10px, 1.2vw, 14px);
  align-items: stretch;
}

.hero {
  border: 1px solid #d1e2ff;
  border-radius: 24px;
  background: linear-gradient(160deg, #e8f3ff, #f6fbff);
  padding: clamp(16px, 2.2vw, 22px);
  display: grid;
  align-content: center;
}

.hero h1 {
  margin: 0 0 6px;
  font-size: clamp(30px, 4.2vw, 46px);
  letter-spacing: -0.03em;
  line-height: 1.04;
  color: #113972;
}

.hero p {
  margin: 0;
  color: #355784;
  font-size: clamp(14px, 1.35vw, 16px);
  line-height: 1.62;
  max-width: 58ch;
}

.hero-grid {
  margin-top: clamp(10px, 1.3vw, 14px);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.hero-cell {
  border: 1px solid #c7dbff;
  border-radius: 12px;
  background: #ffffffc9;
  padding: 8px 9px;
  font-size: 12.5px;
  font-weight: 500;
  color: #3e5f8b;
  text-align: center;
  transition: transform 0.18s ease, border-color 0.18s ease, background-color 0.18s ease;
}

.hero-cell:hover {
  border-color: #b5d1ff;
  background: #ffffff;
  transform: translateY(-1px);
}

.login-panel {
  border: 1px solid #d8e4ff;
  border-radius: 24px;
  background: #ffffffec;
  box-shadow: 0 18px 42px #295ca61d, 0 1px 0 #ffffffa1 inset;
  padding: clamp(14px, 1.7vw, 18px);
  backdrop-filter: blur(6px);
}

.tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: #2153aa;
  border: 1px solid #bfd7ff;
  border-radius: 999px;
  padding: 6px 10px;
  background: #edf4ff;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.login-panel h2 {
  margin: 0 0 4px;
  font-size: clamp(26px, 2.6vw, 30px);
  font-weight: 700;
  letter-spacing: -0.015em;
}

.form-stack {
  display: grid;
  gap: 10px;
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #4b6388;
  margin-bottom: 4px;
}

.password-eye {
  position: absolute;
  right: 8px;
  top: 50%;
  width: 28px;
  height: 28px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #566b8c;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.password-eye:hover {
  background: #edf4ff;
  color: #22487f;
}

.form-row {
  margin-top: 0;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: #5d7396;
  line-height: 1.3;
}

.form-row > span {
  color: #6b81a5;
}

.remember-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.error-slot {
  min-height: 24px;
  display: flex;
  align-items: flex-start;
}

.hint {
  margin-top: 0;
  font-size: 13px;
  color: #bd1b29;
  background: #fff1f3;
  border: 1px solid #ffd0d5;
  border-radius: 10px;
  padding: 5px 8px;
  line-height: 1.5;
}

:deep(.p-inputtext) {
  height: 40px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #ffffffd4;
  color: var(--ink);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

:deep(.p-inputtext::placeholder) {
  color: #6a82a7;
}

:deep(.p-inputtext:enabled:hover) {
  border-color: #a9c8fa;
}

:deep(.p-inputtext:enabled:focus) {
  border-color: #3a7df4;
  box-shadow: 0 0 0 3px #1d68f220;
  background: #fff;
}

:deep(.p-iconfield .p-inputicon) {
  margin-top: -0.5rem;
  color: #6a82a7;
}

:deep(.p-button.login-btn) {
  border: none;
  height: 40px;
  border-radius: 12px;
  font-weight: 700;
  background: linear-gradient(90deg, #1c69f2, #409bff);
  box-shadow: 0 10px 20px #236eea33;
  margin-top: 0;
  transition: transform 0.16s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

:deep(.p-button.login-btn:hover) {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px #236eea3d;
  filter: brightness(1.03);
}

:deep(.p-button.login-btn:active) {
  transform: translateY(0);
}

:deep(.p-checkbox .p-checkbox-box) {
  border-color: #c3d8ff;
}

:global(.dark) .login-page {
  --ink: #dce8ff;
  --paper: #0e1a2d;
  --line: #2f4870;
  --muted: #a6bfdf;
  background: linear-gradient(118deg, #081628 0%, #081628 54%, #0f2947 54%, #0f2947 100%);
}

:global(.dark) .hero {
  border-color: #2b4266;
  background: linear-gradient(160deg, #102640, #0d2038);
}

:global(.dark) .hero h1 {
  color: #d7e6ff;
}

:global(.dark) .hero p,
:global(.dark) .hero-cell {
  color: #aec6e6;
}

:global(.dark) .hero-cell {
  border-color: #35537f;
  background: #112841;
}

:global(.dark) .hero-cell:hover {
  border-color: #436497;
  background: #153150;
}

:global(.dark) .login-panel {
  border-color: #2a4469;
  background: #09182ccc;
  box-shadow: 0 18px 42px #02071266, 0 1px 0 #143457 inset;
}

:global(.dark) .tag {
  color: #9ec3ff;
  border-color: #4168a2;
  background: #0d2544;
}

:global(.dark) .password-eye:hover {
  background: #173454;
  color: #d4e4ff;
}

:global(.dark) :deep(.p-inputtext) {
  background: #10243bcc;
}

:global(.dark) :deep(.p-inputtext:enabled:hover) {
  border-color: #4d6d9a;
}

:global(.dark) :deep(.p-inputtext:enabled:focus) {
  border-color: #6ba0ff;
  box-shadow: 0 0 0 3px #5e96ff2f;
  background: #102840;
}

:global(.dark) .form-row > span {
  color: #93b2de;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
    max-width: 400px;
    justify-items: center;
  }

  .hero {
    display: none;
  }

  .login-panel {
    width: min(390px, 100%);
    padding: 14px;
  }
}

@media (max-width: 520px) {
  .login-page {
    padding: 12px;
  }

  .login-panel {
    padding: 12px;
  }

  .layout {
    gap: 10px;
  }

  .hero-grid {
    grid-template-columns: 1fr;
  }

  .login-panel h2 {
    font-size: 24px;
  }
}
</style>
