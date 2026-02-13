import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy so browser calls don't hit CORS.
// These map to your MVP services:
//  - marketdata-svc:   http://127.0.0.1:8001
//  - run-orchestrator: http://127.0.0.1:8002
//  - results-api:      http://127.0.0.1:8003
//  - regulatory-svc:   http://127.0.0.1:8007
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/mkt": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/mkt/, ""),
      },
      "/orch": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/orch/, ""),
      },
      "/results": {
        target: "http://127.0.0.1:8003",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/results/, ""),
      },
      "/api/v1/regulatory": {
        target: "http://127.0.0.1:8007",
        changeOrigin: true,
      },
    },
  },
});
