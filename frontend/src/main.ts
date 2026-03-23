import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/stores/auth'
import { AppPreset } from '@/theme/preset'
import 'primeicons/primeicons.css'
import './assets/base.css'
import './styles/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
const auth = useAuthStore(pinia)
auth.hydrate()
app.use(router)
app.use(ToastService)
app.use(PrimeVue, {
  theme: {
    preset: AppPreset,
    options: {
      darkModeSelector: '.dark'
    }
  }
})

app.mount('#app')
