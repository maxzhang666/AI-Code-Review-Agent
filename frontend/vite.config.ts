import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const rootDir = resolve(__dirname, '..')
  const env = loadEnv(mode, rootDir, '')

  const proxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [
      vue(),
      Components(),
    ],
    envDir: rootDir,
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes('/zrender/')) return 'vendor-zrender'
            if (id.includes('/echarts/')) return 'vendor-echarts'
            if (id.includes('/primevue/')) return 'vendor-primevue'
            if (id.includes('/@primeuix/')) return 'vendor-prime-theme'
            if (id.includes('/primeicons/')) return 'vendor-prime-icons'
            if (id.includes('lucide-vue-next')) return 'vendor-lucide'
            if (id.includes('vue-router') || id.includes('pinia') || id.includes('/vue/')) return 'vendor-vue'
          }
        }
      }
    }
  }
})
