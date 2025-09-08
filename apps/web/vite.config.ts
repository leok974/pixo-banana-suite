import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // Optional proxy configuration
    proxy: {
      '/pipeline': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/agent': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/edit': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/animate': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/view': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})