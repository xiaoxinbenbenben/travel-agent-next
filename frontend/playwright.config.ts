import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from '@playwright/test'

const currentDir = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: {
    timeout: 8_000
  },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    headless: true,
    trace: 'on-first-retry',
    testIdAttribute: 'data-testid'
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    cwd: currentDir,
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000
  }
})
