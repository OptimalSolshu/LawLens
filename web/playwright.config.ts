import { defineConfig } from "@playwright/test";

// Starts the API in MOCK=1 ([ЖИШЭЭ] sample data, no Neo4j / network) and the Vite dev server.
// E2E_BASE_URL=http://localhost:5173 runs the same test against `docker compose up` instead.
const PY = process.env.PYTHON ?? "../.venv/bin/python";
const external = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: external ?? "http://localhost:4173", viewport: { width: 1440, height: 1000 } },
  webServer: external ? undefined : [
    {
      command: `${PY} -m uvicorn app.main:app --port 8010`,
      cwd: "../backend",
      env: { MOCK: "1" },
      url: "http://localhost:8010/api/health",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npx vite --port 4173 --strictPort",
      env: { VITE_PROXY_TARGET: "http://localhost:8010" },
      url: "http://localhost:4173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
