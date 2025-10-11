import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [react()],
    server: {
      port: Number(env.VITE_DEV_SERVER_PORT || 5173),
      host: env.VITE_DEV_SERVER_HOST || "127.0.0.1",
      proxy: {
        "/api": {
          target: env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
      },
      strictPort: true,
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
