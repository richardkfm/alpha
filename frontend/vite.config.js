import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Inside Docker the backend is reachable at http://backend:8000; for local dev
// (frontend on host) it's http://localhost:8000. BACKEND_ORIGIN lets compose
// override it without touching code.
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://backend:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Proxy API + health so the browser can use same-origin relative paths.
    proxy: {
      '/api': { target: backendOrigin, changeOrigin: true },
      '/health': { target: backendOrigin, changeOrigin: true },
    },
  },
})
