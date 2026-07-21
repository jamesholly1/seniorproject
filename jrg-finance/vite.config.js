import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Port 8000 matches the default in api_server.py. Avoid 5000: macOS
      // AirPlay Receiver binds it, so requests silently hit AirTunes instead.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
