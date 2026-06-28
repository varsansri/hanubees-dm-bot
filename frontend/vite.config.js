import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/hanubees-dm-bot/',
  server: { port: 3000, proxy: { '/api': 'http://localhost:8000', '/oauth': 'http://localhost:8000' } }
})
