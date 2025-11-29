import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/config': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/task': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/refresh': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/results': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/weibo': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/static': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
