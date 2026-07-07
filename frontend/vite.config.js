import http from "node:http";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api -> FastAPI backend, so the frontend never needs to know
// the backend URL or worry about CORS during local development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        // Node >=19 keeps upstream sockets alive by default, but uvicorn closes
        // idle connections after 5s; a request reusing a socket in that instant
        // dies with ECONNRESET. Fresh connections avoid the race (cheap on
        // localhost).
        agent: new http.Agent({ keepAlive: false }),
      },
    },
  },
});
