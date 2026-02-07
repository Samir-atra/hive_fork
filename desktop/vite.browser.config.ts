import { defineConfig } from 'vite'
import path from 'node:path'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
  ],
  optimizeDeps: {
    include: ['react', 'react-dom', 'framer-motion', 'lucide-react'],
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Stub out node-specific modules for browser run
      'nodejs-polars': path.resolve(__dirname, './src/stubs/polars-stub.ts'),
    },
  },
  define: {
    // Provide a dummy value for process.env if needed, though Vite usually handles this
    'process.env': {}
  }
})
