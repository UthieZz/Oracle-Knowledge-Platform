import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Live Studio stays on :3000. Flask api_server stays on :5000.
// Proxy only; Studio is not a compiler.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
});
