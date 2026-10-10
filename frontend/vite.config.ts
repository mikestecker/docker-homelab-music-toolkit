import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    // In dev, run the FastAPI backend separately (e.g. on :8095) and proxy
    // API calls to it so the browser's native Basic Auth prompt still works
    // against the same origin the page is served from.
    proxy: {
      "/api": "http://127.0.0.1:8095",
      "/healthz": "http://127.0.0.1:8095",
    },
  },
});
