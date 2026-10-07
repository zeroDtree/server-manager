#!/usr/bin/env node
/**
 * Capture GSAD console screenshots for the manuals.
 *
 * Prerequisites: Vite UI on :5173 and the mock backend stack.
 *
 *   PLAYWRIGHT_ROOT=/tmp/gsad-playwright node docs/scripts/capture-screenshots.mjs
 *   GSAD_DOCS_LOCALE=zh PLAYWRIGHT_ROOT=/tmp/gsad-playwright node docs/scripts/capture-screenshots.mjs
 *
 * Writes 1440×900 @ 2x PNGs to docs/assets/<en|zh>/. Overwrites the same kebab-case
 * names the manuals reference. Does not capture OS file pickers. Leaves agent PSKs
 * masked except on Add server after Generate (a fresh random value).
 */

import { createRequire } from 'node:module'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(
  path.join(process.env.PLAYWRIGHT_ROOT || '/tmp/gsad-playwright', 'package.json'),
)
const { chromium } = require('playwright')

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../..')
const DOCS_LOCALE = process.env.GSAD_DOCS_LOCALE === 'zh' ? 'zh' : 'en'
const OUT_DIR = path.join(REPO_ROOT, 'docs/assets', DOCS_LOCALE)
const BASE = process.env.GSAD_DOCS_BASE_URL || 'http://localhost:5173'
const ADMIN_EMAIL = process.env.GSAD_DOCS_ADMIN_EMAIL || 'admin@gsad.local'
const ADMIN_PASSWORD = process.env.GSAD_DOCS_ADMIN_PASSWORD || 'Admin@123456'

const UI = {
  en: {
    playwrightLocale: 'en-US',
    storageLocale: 'en',
    close: 'Close',
    refresh: 'Refresh',
    signIn: 'Sign in',
    newApplication: 'New application',
    targetServer: 'Target server',
    submit: 'Submit application',
    authorizing: 'Authorizing',
    active: 'Active',
    connectionInfo: 'Connection info',
    revoke: 'Revoke access',
    revoking: 'Revoking',
    revoked: 'Revoked',
    changePassword: 'Change login password',
    userManagement: 'User management',
    importUsers: 'Import users',
    startImport: 'Start import',
    importComplete: 'Import complete',
    serverManagement: 'Server management',
    addServer: 'Add server',
    addServerHint: 'server_id and agent PSK',
    generate: 'Generate',
    cancel: 'Cancel',
    importCsv: 'Import CSV',
    settings: 'Settings',
    loginRateLimit: 'Login rate limit',
  },
  zh: {
    playwrightLocale: 'zh-CN',
    storageLocale: 'zh-CN',
    close: '关闭',
    refresh: '刷新',
    signIn: '登录',
    newApplication: '新建申请',
    targetServer: '目标服务器',
    submit: '提交申请',
    authorizing: '授权处理中',
    active: '已生效',
    connectionInfo: '连接信息',
    revoke: '撤销访问',
    revoking: '回收中',
    revoked: '已撤销',
    changePassword: '修改登录密码',
    userManagement: '用户管理',
    importUsers: '导入用户',
    startImport: '开始导入',
    importComplete: '导入完成',
    serverManagement: '服务器管理',
    addServer: '添加服务器',
    addServerHint: 'server_id 与 agent PSK',
    generate: '生成',
    cancel: '取消',
    importCsv: '导入 CSV',
    settings: '系统设置',
    loginRateLimit: '登录限流',
  },
}

const ui = UI[DOCS_LOCALE]

const USER_CSV = `email,linux_username,display_name,student_id,cohort,initial_password,roles
alice@example.com,alice,Alice,2024001,2024,InitialPass1,user
`
const SERVER_CSV = `server_id,agent_psk
gpu-docs-01,0123456789abcdef
gpu-docs-02,fedcba9876543210
`

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function dismissToasts(page) {
  const toastCloses = page.locator(
    `[aria-live="polite"] button[aria-label="${ui.close}"]`,
  )
  const n = await toastCloses.count()
  for (let i = 0; i < n; i += 1) {
    await toastCloses.nth(i).click({ timeout: 500 }).catch(() => {})
  }
}

async function closeOverlay(page) {
  const panelClose = page.locator(
    `.relative.z-10 button[aria-label="${ui.close}"]`,
  )
  if (await panelClose.count()) {
    await panelClose.last().click({ timeout: 3000 })
    await page
      .locator('.fixed.inset-0.z-50')
      .first()
      .waitFor({ state: 'hidden', timeout: 3000 })
      .catch(() => {})
    await sleep(200)
    return
  }
  const dialogClose = page.locator(
    `[role="dialog"] button[aria-label="${ui.close}"]`,
  )
  if (await dialogClose.count()) {
    await dialogClose.first().click({ timeout: 3000 })
    await page
      .locator('[role="dialog"]')
      .waitFor({ state: 'hidden', timeout: 3000 })
      .catch(() => {})
    await sleep(200)
  }
}

async function openApplicationRow(page, serverId) {
  await dismissToasts(page)
  await page.locator('tbody tr', { hasText: serverId }).first().click()
  await page.locator('[role="dialog"]').waitFor({ timeout: 10_000 })
  await sleep(300)
}

async function clickRefresh(page) {
  const refresh = page.getByRole('button', { name: ui.refresh })
  if (await refresh.count()) {
    await refresh.click().catch(() => {})
  }
}

async function waitForRowStatus(page, serverId, status, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const loc = page.locator('tbody tr', { hasText: serverId }).getByText(status)
    if ((await loc.count()) > 0 && (await loc.first().isVisible().catch(() => false))) {
      return
    }
    await clickRefresh(page)
    await sleep(1500)
  }
  throw new Error(`timed out waiting for ${status} on ${serverId}`)
}

async function shot(page, name) {
  await dismissToasts(page)
  await sleep(250)
  const dest = path.join(OUT_DIR, name)
  await page.screenshot({
    path: dest,
    animations: 'disabled',
    type: 'png',
  })
  console.log(`wrote ${path.relative(REPO_ROOT, dest)}`)
}

async function goto(page, pathname) {
  await page.goto(new URL(pathname, BASE).toString(), { waitUntil: 'networkidle' })
  await page.waitForSelector('text=GSAD')
  await sleep(400)
}

async function main() {
  console.log(`capturing locale=${DOCS_LOCALE} → ${path.relative(REPO_ROOT, OUT_DIR)}`)
  await mkdir(OUT_DIR, { recursive: true })
  const tmpDir = await mkdtemp(path.join(os.tmpdir(), 'gsad-docs-csv-'))
  const userCsvPath = path.join(tmpDir, 'users.csv')
  const serverCsvPath = path.join(tmpDir, 'servers.csv')
  await writeFile(userCsvPath, USER_CSV)
  await writeFile(serverCsvPath, SERVER_CSV)

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    locale: ui.playwrightLocale,
    colorScheme: 'light',
  })
  await context.addInitScript((storageLocale) => {
    localStorage.setItem('gsad-locale', storageLocale)
  }, ui.storageLocale)
  const page = await context.newPage()

  await goto(page, '/login')
  await page.waitForSelector('#login-email')
  await shot(page, 'login.png')

  await page.locator('#login-email').fill(ADMIN_EMAIL)
  await page.locator('#login-password').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: ui.signIn }).click()
  await page.waitForURL('**/board')
  await page.getByText('gpu-mock-001', { exact: true }).waitFor({ timeout: 30_000 })
  await sleep(500)
  await shot(page, 'board.png')

  await goto(page, '/applications/new')
  await page.getByRole('heading', { name: ui.newApplication }).waitFor()
  await shot(page, 'apply.png')

  await goto(page, '/applications/new?serverId=gpu-mock-003')
  await page.waitForFunction(() => {
    const select = document.querySelector('#f-server-id')
    return select instanceof HTMLSelectElement && select.value === 'gpu-mock-003'
  })
  await shot(page, 'apply-target.png')

  const targetServer = `gpu-mock-${String(20 + Math.floor(Math.random() * 80)).padStart(3, '0')}`
  await page.getByLabel(ui.targetServer).selectOption(targetServer)
  await page.getByRole('button', { name: ui.submit }).click()
  await page.waitForURL('**/applications/mine**')
  await dismissToasts(page)
  await sleep(300)
  await shot(page, 'applications.png')

  if (
    (await page
      .locator('tbody tr', { hasText: targetServer })
      .getByText(ui.authorizing)
      .count()) > 0
  ) {
    await openApplicationRow(page, targetServer)
    await shot(page, 'application-authorizing.png')
    await closeOverlay(page)
    await goto(page, '/applications/mine')
  }

  await waitForRowStatus(page, targetServer, ui.active)
  await openApplicationRow(page, targetServer)
  await page.getByText(ui.connectionInfo).waitFor()
  await shot(page, 'application-detail.png')

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: ui.revoke }).click()
  await page
    .locator('[role="dialog"]')
    .getByText(ui.revoking)
    .first()
    .waitFor({ timeout: 15_000 })
  await sleep(250)
  await shot(page, 'application-revoking.png')
  await closeOverlay(page)
  await waitForRowStatus(page, targetServer, ui.revoked)
  await openApplicationRow(page, targetServer)
  await page.locator('[role="dialog"]').getByText(ui.revoked, { exact: true }).waitFor()
  await sleep(300)
  await shot(page, 'application-revoked.png')
  await closeOverlay(page)

  await goto(page, '/account/password')
  await page.getByRole('heading', { name: ui.changePassword }).waitFor()
  await shot(page, 'change-password.png')

  await goto(page, '/admin/users')
  await page.getByRole('heading', { name: ui.userManagement }).waitFor()

  await page.getByRole('button', { name: ui.importUsers }).click()
  await page.locator('#user-csv').waitFor({ state: 'visible', timeout: 10_000 })
  await shot(page, 'admin-users-import.png')
  await page.locator('#user-csv').setInputFiles(userCsvPath)
  await sleep(200)
  await shot(page, 'admin-users-import-ready.png')
  await page.getByRole('button', { name: ui.startImport }).click()
  await page.getByText(ui.importComplete).first().waitFor({ timeout: 15_000 })
  await sleep(250)
  await shot(page, 'admin-users-import-result.png')
  await closeOverlay(page)
  await sleep(300)
  await shot(page, 'admin-users.png')

  await page.locator('tbody tr', { hasText: 'alice@example.com' }).click()
  await page.locator('[role="dialog"]').waitFor()
  await sleep(300)
  await shot(page, 'admin-user-detail.png')
  await closeOverlay(page)

  await goto(page, '/admin/servers')
  await page.getByRole('heading', { name: ui.serverManagement }).waitFor()
  await page.getByText('gpu-mock-001').waitFor()
  await shot(page, 'admin-servers.png')

  await page.getByRole('button', { name: ui.addServer }).click()
  await page.getByText(ui.addServerHint).waitFor()
  await page.locator('#s-server-id').fill('gpu-docs-01')
  await page.getByRole('button', { name: ui.generate }).click()
  await sleep(200)
  await shot(page, 'admin-servers-add.png')
  await page.getByRole('button', { name: ui.cancel }).click()

  await page.locator('tbody tr', { hasText: 'gpu-mock-001' }).click()
  await page.locator('[role="dialog"]').waitFor()
  await sleep(300)
  await shot(page, 'admin-server-detail.png')
  await closeOverlay(page)

  await page.getByRole('button', { name: ui.importCsv }).click()
  await page.locator('#server-csv').waitFor({ state: 'visible', timeout: 10_000 })
  await shot(page, 'admin-servers-import.png')
  await page.locator('#server-csv').setInputFiles(serverCsvPath)
  await sleep(200)
  await shot(page, 'admin-servers-import-ready.png')
  await page.getByRole('button', { name: ui.startImport }).click()
  await page.getByText(ui.importComplete).first().waitFor({ timeout: 15_000 })
  await sleep(250)
  await shot(page, 'admin-servers-import-result.png')
  await closeOverlay(page)

  await goto(page, '/admin/settings')
  await page.getByRole('heading', { name: ui.settings }).waitFor()
  await page.getByText(ui.loginRateLimit).waitFor()
  await shot(page, 'admin-settings.png')

  await browser.close()
  console.log('done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
