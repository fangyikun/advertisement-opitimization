import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// GitHub Pages: 若部署到 https://username.github.io/仓库名/，则 base 设为 '/仓库名/'
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || '/',
})
