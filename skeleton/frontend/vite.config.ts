import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  server: {
    hmr: { overlay: false },
    proxy: {
      '/online': { target: 'http://backend:8080', changeOrigin: true }
    }
  }
})
