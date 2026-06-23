import { defineConfig } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'

// Inside Docker the backend is reachable at http://backend:8000; for local dev
// (frontend on host) it's http://localhost:8000. BACKEND_ORIGIN lets compose
// override it without touching code.
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://backend:8000'

// Hostnames allowed to reach the dev server. Vite rejects requests whose Host
// header it doesn't recognise, which blocks access through a reverse proxy or
// tunnel (Cloudflare Tunnel, Nginx, …) on a custom domain. Set
// ALPHA_ALLOWED_HOSTS to a comma-separated list of those domains, or "all"/"*"
// to allow any host. localhost / 127.0.0.1 are always permitted by Vite.
const allowedHostsEnv = (process.env.ALPHA_ALLOWED_HOSTS || '').trim()
const allowedHosts =
  allowedHostsEnv === 'all' || allowedHostsEnv === '*'
    ? true
    : allowedHostsEnv
        .split(',')
        .map((h) => h.trim())
        .filter(Boolean)

export default defineConfig({
  plugins: [vue()],
  // Two entry points: the full app (index.html) and the lightweight embeddable
  // widget (embed.html), so the iframe build never includes the globe/map bundle.
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        embed: resolve(__dirname, 'embed.html'),
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts,
    // Proxy API + health so the browser can use same-origin relative paths.
    proxy: {
      '/api': { target: backendOrigin, changeOrigin: true },
      '/health': { target: backendOrigin, changeOrigin: true },
    },
  },
})
