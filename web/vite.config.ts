import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В разработке API живёт на uvicorn :8000, в продакшене — на том же origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
