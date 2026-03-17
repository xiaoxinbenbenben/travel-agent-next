import { expect, test } from '@playwright/test'
import { sampleTripPlan } from './fixtures/trip-plan'

test('home submit should create trip and navigate to result', async ({ page }) => {
  let capturedPayload: Record<string, unknown> | undefined
  let photoRequestCount = 0

  await page.addInitScript(() => {
    window.__TRAVEL_AGENT_E2E__ = true
  })

  await page.route('**/api/trip/plan', async (route) => {
    capturedPayload = route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: '旅行计划生成成功',
        data: sampleTripPlan
      })
    })
  })

  await page.route('**/api/poi/photo?*', async (route) => {
    photoRequestCount += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: '获取图片成功',
        data: {
          name: 'placeholder',
          photo_url: 'https://images.example.com/travel.jpg'
        }
      })
    })
  })

  await page.goto('/')

  await expect(page.getByText('熟悉的填写方式')).toHaveCount(0)
  await expect(page.getByText('升级保留什么')).toHaveCount(0)
  await expect(page.getByText('兼容旧逻辑')).toHaveCount(0)

  await page.getByTestId('city-input').fill('杭州')
  await page.getByTestId('start-date-picker').locator('input').fill('2026-04-03')
  await page.getByTestId('end-date-picker').locator('input').fill('2026-04-05')
  await page.getByTestId('free-text-input').fill('想看西湖夜景，也想吃本地菜。')

  await page.getByTestId('submit-trip-button').click()

  await expect(page).toHaveURL(/\/result$/)
  await expect(page.getByRole('heading', { name: '杭州旅行计划' })).toBeVisible()
  await expect(page.getByText('页面结构和功能流程延续旧版')).toHaveCount(0)
  await expect(page.locator('#budget')).toBeVisible()
  await expect(page.locator('.ant-collapse-header').filter({ hasText: '第1天' }).first()).toBeVisible()
  await expect
    .poll(() => photoRequestCount)
    .toBe(0)

  await expect
    .poll(() => capturedPayload?.travel_days)
    .toBe(3)
  await expect
    .poll(() => capturedPayload?.city)
    .toBe('杭州')
})
