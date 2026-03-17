import { expect, test } from '@playwright/test'
import { sampleTripPlan } from './fixtures/trip-plan'

test.beforeEach(async ({ page }) => {
  await page.addInitScript((tripPlan) => {
    window.__TRAVEL_AGENT_E2E__ = true
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan))
    ;(window as Window & { __DOWNLOADS__?: Array<{ download: string; href: string }> }).__DOWNLOADS__ = []
    HTMLAnchorElement.prototype.click = function click() {
      const store = window as Window & {
        __DOWNLOADS__?: Array<{ download: string; href: string }>
      }
      store.__DOWNLOADS__?.push({
        download: this.download,
        href: this.href
      })
    }
  }, sampleTripPlan)

  await page.route('**/api/poi/photo?*', async (route) => {
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
})

test('result page should support edit save and cancel', async ({ page }) => {
  await page.goto('/result')

  await expect(page.getByRole('heading', { name: '杭州旅行计划' })).toBeVisible()
  await expect(page.getByText('页面结构和功能流程延续旧版')).toHaveCount(0)
  await expect(page.locator('.ticket-price')).toHaveCount(0)
  await expect(page.getByTestId('hotel-card-0').getByText('价格范围')).toHaveCount(0)
  await expect(page.getByTestId('hotel-card-0').getByText('评分')).toHaveCount(0)
  await expect(page.getByTestId('hotel-card-0').getByText('距离')).toHaveCount(0)

  await page.getByTestId('edit-trip-button').click()
  await page
    .getByTestId('attraction-address-input-0-0')
    .fill('杭州市西湖区断桥景观带 1 号')
  await page.getByTestId('save-trip-button').click()

  await expect(page.getByText('修改已保存')).toBeVisible()
  await expect(page.getByText('杭州市西湖区断桥景观带 1 号')).toBeVisible()

  await page.getByTestId('edit-trip-button').click()
  await page
    .getByTestId('attraction-address-input-0-0')
    .fill('这条修改应该在取消后回滚')
  await page.getByTestId('cancel-edit-button').click()

  await expect(page.getByText('已取消编辑')).toBeVisible()
  await expect(page.getByText('杭州市西湖区断桥景观带 1 号')).toBeVisible()
  await expect(page.getByText('这条修改应该在取消后回滚')).toHaveCount(0)
})

test('result page export buttons should trigger download flow', async ({ page }) => {
  await page.goto('/result')

  await page.getByTestId('export-trigger').click()
  await page.getByText('导出为图片').click()
  await expect(page.getByText('图片导出成功')).toBeVisible()

  await page.getByTestId('export-trigger').click()
  await page.getByText('导出为PDF').click()
  await expect(page.getByText('PDF导出成功')).toBeVisible()

  await expect
    .poll(async () => {
      return page.evaluate(() => {
        const store = window as Window & {
          __DOWNLOADS__?: Array<{ download: string; href: string }>
        }
        return store.__DOWNLOADS__?.length ?? 0
      })
    })
    .toBe(2)
})

test('result page should not request extra photo lookups and should show no-photo state', async ({ page }) => {
  let photoRequestCount = 0

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
          photo_url: 'https://source.unsplash.com/featured/?bad-url'
        }
      })
    })
  })

  await page.goto('/result')

  await expect
    .poll(() => photoRequestCount)
    .toBe(0)
  await expect(page.getByTestId('attraction-photo-empty-0-0')).toBeVisible()
  await expect(page.locator('[data-testid="attraction-photo-frame-0-0"] img')).toHaveCount(0)
})
