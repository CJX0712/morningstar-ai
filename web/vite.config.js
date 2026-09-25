import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api 统一反代到 rag-api（开发期走 localhost:8000，生产 nginx 同理）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
