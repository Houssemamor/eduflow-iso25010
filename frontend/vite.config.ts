import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The dev server forwards every /api call to the backend so the browser only
// talks to one origin and no CORS configuration is required during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Inside Compose the API is reachable by service name; locally it is
        // on localhost. The override prevents a 502 from the container.
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
