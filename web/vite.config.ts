import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api is proxied to the backend, so the default VITE_API_BASE ("") works in dev and docker.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": process.env.VITE_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
});
