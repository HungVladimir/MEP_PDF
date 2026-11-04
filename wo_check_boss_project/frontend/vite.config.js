import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Khi dev: /api được chuyển sang backend FastAPI ở cổng 8000
export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE || '/',
  server: {
    port: 5173,
    proxy: { '/api': { target: process.env.VITE_BACKEND || 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})