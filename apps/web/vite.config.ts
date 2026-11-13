// Vite: React plugin, dev server on PORT (default 5173), production build to dist/.
// API_PROXY_TARGET (environment or .env), when set, proxies /api to that URL with the /api prefix removed (dev only).
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.API_PROXY_TARGET ?? loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), '').API_PROXY_TARGET;

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT ?? 5173),
    ...(apiTarget ? { proxy: { '/api': { target: apiTarget, changeOrigin: true, rewrite: (path: string) => path.replace(/^\/api/, '') } } } : {})
  },
  build: { outDir: 'dist', sourcemap: true }
});
