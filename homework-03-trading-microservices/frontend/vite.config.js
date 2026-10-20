import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api/<name>/... -> http://localhost:<port>/... (ports from docker-compose.yml)
const SERVICES = {
  'market-data': 8001,
  'pricing': 8002,
  'monitoring': 8003,
  'books': 8004,
  'blotter': 8006,
  'trade-generation': 8007,
  'trade-action': 8008,
}

const proxy = Object.fromEntries(
  Object.entries(SERVICES).map(([name, port]) => [
    `/api/${name}`,
    {
      // 127.0.0.1, not localhost: Node resolves localhost to IPv6 ::1, which on Windows goes via wslrelay and can hang
      target: `http://127.0.0.1:${port}`,
      changeOrigin: true,
      rewrite: (path) => path.replace(`/api/${name}`, ''),
      // Runs before Vite's own handler (which answers a bare 500), so the UI can tell "service down" from a crash
      configure: (proxyServer) => {
        proxyServer.on('error', (err, req, res) => {
          if (!('writeHead' in res) || res.headersSent || res.writableEnded) return
          res.writeHead(503, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ error: `${name} service unavailable` }))
        })
      },
    },
  ]),
)

export default defineConfig({
  plugins: [react()],
  css: {
    preprocessorOptions: {
      scss: { api: 'modern-compiler' },
    },
  },
  server: {
    port: 5173,
    // Dev-only proxy: browser talks to :5173 only, so no CORS on the Python side
    proxy,
  },
})
