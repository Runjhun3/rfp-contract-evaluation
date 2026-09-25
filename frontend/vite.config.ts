/// <reference types="vitest/config" />
// Dev: `npm run dev` serves the UI on http://localhost:5173 and proxies /api to
// the Python API on 127.0.0.1:8000. Build: `npm run build` writes dist/, which
// the Python app serves in production (no Node at runtime).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist", sourcemap: false },
  test: { environment: "node" },
});
