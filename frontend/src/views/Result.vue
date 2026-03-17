<template>
  <div class="result-view fade-rise">
    <div class="result-header glass-panel">
      <div class="header-copy">
        <span class="section-kicker">Trip Atlas</span>
        <h2 class="result-title">{{ tripPlan ? `${tripPlan.city}旅行计划` : '旅行结果总览' }}</h2>
        <p class="supporting-text">
          从整体路线到每日安排、地图、天气和预算，你可以先浏览全貌，再把细节调整到最适合自己的节奏。
        </p>
      </div>

      <div class="header-actions">
        <a-button size="large" @click="goBack">返回首页</a-button>
        <a-button
          v-if="!editMode"
          size="large"
          data-testid="edit-trip-button"
          @click="toggleEditMode"
        >
          编辑行程
        </a-button>
        <a-button
          v-else
          type="primary"
          size="large"
          data-testid="save-trip-button"
          @click="saveChanges"
        >
          保存修改
        </a-button>
        <a-button
          v-if="editMode"
          size="large"
          data-testid="cancel-edit-button"
          @click="cancelEdit"
        >
          取消编辑
        </a-button>
        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu @click="handleExportClick">
              <a-menu-item key="image">导出为图片</a-menu-item>
              <a-menu-item key="pdf">导出为PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button size="large" data-testid="export-trigger">
            导出行程
            <DownOutlined />
          </a-button>
        </a-dropdown>
      </div>
    </div>

    <div v-if="tripPlan" class="result-layout">
      <aside class="result-side-nav">
        <a-affix :offset-top="108">
          <a-menu
            mode="inline"
            :selected-keys="[activeSection]"
            @click="scrollToSection"
          >
            <a-menu-item key="overview">行程概览</a-menu-item>
            <a-menu-item v-if="tripPlan.budget" key="budget">预算明细</a-menu-item>
            <a-menu-item key="map">景点地图</a-menu-item>
            <a-sub-menu key="days" title="每日行程">
              <a-menu-item
                v-for="(day, index) in tripPlan.days"
                :key="`day-${index}`"
              >
                第{{ day.day_index + 1 }}天
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item
              v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0"
              key="weather"
            >
              天气信息
            </a-menu-item>
          </a-menu>
        </a-affix>
      </aside>

      <div class="result-main" id="result-export-target">
        <section class="top-overview">
          <div class="top-left-stack">
            <a-card id="overview" :bordered="false" class="overview-card">
              <template #title>
                <div class="card-title-row">
                  <span>{{ tripPlan.city }}旅行计划</span>
                  <span class="overview-pill">{{ tripPlan.days.length }} 天路线</span>
                </div>
              </template>

              <div class="overview-grid">
                <div class="overview-item">
                  <span class="overview-label">出行日期</span>
                  <strong>{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</strong>
                </div>
                <div class="overview-item">
                  <span class="overview-label">整体建议</span>
                  <p>{{ tripPlan.overall_suggestions }}</p>
                </div>
              </div>
            </a-card>

            <a-card
              v-if="tripPlan.budget"
              id="budget"
              title="预算明细"
              :bordered="false"
              class="budget-card"
            >
              <div class="budget-grid">
                <div class="budget-stat">
                  <span>景点门票</span>
                  <strong>¥{{ tripPlan.budget.total_attractions }}</strong>
                </div>
                <div class="budget-stat">
                  <span>酒店住宿</span>
                  <strong>¥{{ tripPlan.budget.total_hotels }}</strong>
                </div>
                <div class="budget-stat">
                  <span>餐饮费用</span>
                  <strong>¥{{ tripPlan.budget.total_meals }}</strong>
                </div>
                <div class="budget-stat">
                  <span>交通费用</span>
                  <strong>¥{{ tripPlan.budget.total_transportation }}</strong>
                </div>
              </div>
              <div class="budget-total">
                <span>预估总费用</span>
                <strong>¥{{ tripPlan.budget.total }}</strong>
              </div>
            </a-card>
          </div>

          <a-card id="map" title="景点地图" :bordered="false" class="map-card">
            <div v-if="hasMapConfig" id="amap-container" class="map-surface"></div>
            <div v-else class="map-fallback">
              <span>Map service</span>
              <strong>地图暂时不可用</strong>
              <p>你仍然可以先查看文字版行程、预算和天气信息。</p>
            </div>
            <p v-if="mapError" class="map-error">{{ mapError }}</p>
          </a-card>
        </section>

        <a-card title="每日行程" :bordered="false" class="days-card">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="String(index)"
            >
              <template #header>
                <div class="day-panel-header">
                  <div>
                    <strong>第{{ day.day_index + 1 }}天</strong>
                    <span>{{ day.date }}</span>
                  </div>
                  <small>{{ day.transportation }}</small>
                </div>
              </template>

              <div :id="`day-${index}`" class="day-anchor"></div>

              <div class="day-summary-panel">
                <div class="day-summary-item">
                  <span>行程描述</span>
                  <strong>{{ day.description }}</strong>
                </div>
                <div class="day-summary-item">
                  <span>交通方式</span>
                  <strong>{{ day.transportation }}</strong>
                </div>
                <div class="day-summary-item">
                  <span>住宿偏好</span>
                  <strong>{{ day.accommodation }}</strong>
                </div>
              </div>

              <a-divider orientation="left">景点安排</a-divider>
              <a-list :data-source="day.attractions" :grid="{ gutter: 18, xs: 1, sm: 1, md: 2 }">
                <template #renderItem="{ item, index: attractionIndex }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <template v-if="editMode" #extra>
                        <a-space>
                          <a-button
                            size="small"
                            :disabled="attractionIndex === 0"
                            @click="moveAttraction(day.day_index, attractionIndex, 'up')"
                          >
                            上移
                          </a-button>
                          <a-button
                            size="small"
                            :disabled="attractionIndex === day.attractions.length - 1"
                            @click="moveAttraction(day.day_index, attractionIndex, 'down')"
                          >
                            下移
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, attractionIndex)"
                          >
                            删除
                          </a-button>
                        </a-space>
                      </template>

                      <div
                        class="attraction-media"
                        :data-testid="`attraction-photo-frame-${day.day_index}-${attractionIndex}`"
                      >
                        <img
                          v-if="getAttractionImageUrl(item, day.day_index, attractionIndex)"
                          :src="getAttractionImageUrl(item, day.day_index, attractionIndex) || ''"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handleAttractionImageError(item, day.day_index, attractionIndex)"
                        />
                        <div
                          v-else
                          class="attraction-image-empty"
                          :data-testid="`attraction-photo-empty-${day.day_index}-${attractionIndex}`"
                        >
                          <span class="attraction-empty-kicker">No photo found</span>
                          <strong>{{ item.name }}</strong>
                          <p>暂未找到合适的景点图片</p>
                        </div>
                        <span class="attraction-order">{{ attractionIndex + 1 }}</span>
                      </div>

                      <div v-if="editMode" class="attraction-edit-fields">
                        <label class="field-label">
                          地址
                          <a-input
                            :data-testid="`attraction-address-input-${day.day_index}-${attractionIndex}`"
                            v-model:value="item.address"
                          />
                        </label>
                        <label class="field-label">
                          游览时长（分钟）
                          <a-input-number
                            v-model:value="item.visit_duration"
                            :min="10"
                            :max="480"
                            style="width: 100%"
                          />
                        </label>
                        <label class="field-label">
                          描述
                          <a-textarea
                            v-model:value="item.description"
                            :rows="3"
                          />
                        </label>
                      </div>

                      <div v-else class="attraction-meta">
                        <p><strong>地址：</strong>{{ item.address }}</p>
                        <p><strong>游览时长：</strong>{{ item.visit_duration }} 分钟</p>
                        <p><strong>描述：</strong>{{ item.description }}</p>
                        <p v-if="item.rating"><strong>评分：</strong>{{ item.rating }} ⭐</p>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <template v-if="day.hotel">
                <a-divider orientation="left">住宿推荐</a-divider>
                <div
                  class="hotel-card glass-panel"
                  :data-testid="`hotel-card-${day.day_index}`"
                >
                  <div class="hotel-card-header">
                    <span class="hotel-kicker">Stay</span>
                    <h4 class="hotel-name">{{ day.hotel.name }}</h4>
                    <p class="hotel-type">{{ day.hotel.type || day.accommodation }}</p>
                  </div>
                  <div class="hotel-card-body">
                    <div class="hotel-detail">
                      <span>地址</span>
                      <strong>{{ day.hotel.address }}</strong>
                    </div>
                    <div class="hotel-detail">
                      <span>建议风格</span>
                      <strong>{{ day.accommodation }}</strong>
                    </div>
                  </div>
                </div>
              </template>

              <a-divider orientation="left">餐饮安排</a-divider>
              <div class="meal-grid">
                <article
                  v-for="meal in day.meals"
                  :key="meal.type"
                  class="meal-card glass-panel"
                >
                  <span class="meal-label">{{ getMealLabel(meal.type) }}</span>
                  <h5 class="meal-name">{{ meal.name }}</h5>
                  <p class="meal-description">
                    {{ meal.description || '为这段行程补上一餐刚刚好的在地风味。' }}
                  </p>
                  <span v-if="meal.address" class="meal-address">{{ meal.address }}</span>
                </article>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <a-card
          v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0"
          id="weather"
          title="天气信息"
          :bordered="false"
          class="weather-card-shell"
        >
          <a-list :data-source="tripPlan.weather_info" :grid="{ gutter: 18, xs: 1, sm: 2, md: 3 }">
            <template #renderItem="{ item }">
              <a-list-item>
                <div class="weather-card glass-panel">
                  <strong>{{ item.date }}</strong>
                  <div class="weather-row">
                    <span>白天</span>
                    <span>{{ item.day_weather }} · {{ normalizeTemperature(item.day_temp) }}</span>
                  </div>
                  <div class="weather-row">
                    <span>夜间</span>
                    <span>{{ item.night_weather }} · {{ normalizeTemperature(item.night_temp) }}</span>
                  </div>
                  <div class="weather-row weather-wind">
                    <span>风向 / 风力</span>
                    <span>{{ item.wind_direction }} {{ item.wind_power }}</span>
                  </div>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </div>
    </div>

    <a-empty v-else description="没有找到旅行计划数据">
      <template #description>
        <span class="empty-copy">当前没有可展示的行程数据，请先回到首页创建旅行计划。</span>
      </template>
      <a-button type="primary" @click="goBack">返回首页创建行程</a-button>
    </a-empty>

    <a-back-top :visibility-height="280">
      <div class="back-top-button">↑</div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import type { Attraction, DayPlan, TripPlan } from '@/types'
import { getMealLabel, isTrustedAttractionImageUrl, normalizeTemperature } from '@/utils/attractions'
import { exportElementAsImage, exportElementAsPdf } from '@/utils/export'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const hiddenAttractionImages = ref<Record<string, boolean>>({})
const activeSection = ref('overview')
const activeDays = ref<string | string[]>('0')
const mapError = ref('')

const hasMapConfig = computed(() => {
  return Boolean(
    import.meta.env.VITE_AMAP_API_KEY &&
      import.meta.env.VITE_AMAP_SECURITY_JS_CODE
  )
})

let map: any = null

function clonePlan(plan: TripPlan): TripPlan {
  return JSON.parse(JSON.stringify(plan)) as TripPlan
}

function getDayByIndex(dayIndex: number): DayPlan | undefined {
  return tripPlan.value?.days.find((day) => day.day_index === dayIndex)
}

async function loadTripPlan(): Promise<void> {
  const cachedPlan = sessionStorage.getItem('tripPlan')
  if (!cachedPlan) {
    return
  }

  try {
    tripPlan.value = JSON.parse(cachedPlan) as TripPlan
    await nextTick()
    await initMap()
  } catch (error) {
    message.error('行程数据解析失败，请重新生成')
    sessionStorage.removeItem('tripPlan')
    console.error(error)
  }
}

function buildAttractionImageKey(dayIndex: number, attractionIndex: number, attractionName: string): string {
  return `${dayIndex}-${attractionIndex}-${attractionName}`
}

function getAttractionImageUrl(
  attraction: Attraction,
  dayIndex: number,
  attractionIndex: number
): string | null {
  const imageKey = buildAttractionImageKey(dayIndex, attractionIndex, attraction.name)
  if (hiddenAttractionImages.value[imageKey]) {
    return null
  }

  const imageCandidates = [
    attraction.image_url,
    attraction.photos?.[0]
  ]

  return imageCandidates.find((url) => isTrustedAttractionImageUrl(url)) ?? null
}

function handleAttractionImageError(
  attraction: Attraction,
  dayIndex: number,
  attractionIndex: number
): void {
  const imageKey = buildAttractionImageKey(dayIndex, attractionIndex, attraction.name)
  hiddenAttractionImages.value[imageKey] = true
}

function goBack(): void {
  void router.push('/')
}

function scrollToSection({ key }: { key: string }): void {
  activeSection.value = key

  if (key.startsWith('day-')) {
    activeDays.value = key.replace('day-', '')
  }

  window.setTimeout(() => {
    document.getElementById(key)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }, 120)
}

function toggleEditMode(): void {
  if (!tripPlan.value) {
    return
  }

  originalPlan.value = clonePlan(tripPlan.value)
  editMode.value = true
  message.info('进入编辑模式')
}

function resetMap(): void {
  if (map) {
    map.destroy()
    map = null
  }
}

function saveChanges(): void {
  if (!tripPlan.value) {
    return
  }

  editMode.value = false
  sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  message.success('修改已保存')
  resetMap()
  void nextTick(() => initMap())
}

function cancelEdit(): void {
  if (originalPlan.value) {
    tripPlan.value = clonePlan(originalPlan.value)
  }

  editMode.value = false
  message.info('已取消编辑')
  resetMap()
  void nextTick(() => initMap())
}

function deleteAttraction(dayIndex: number, attractionIndex: number): void {
  const day = getDayByIndex(dayIndex)
  if (!day) {
    return
  }

  if (day.attractions.length <= 1) {
    message.warning('每天至少保留一个景点')
    return
  }

  day.attractions.splice(attractionIndex, 1)
  message.success('景点已删除')
}

function moveAttraction(dayIndex: number, attractionIndex: number, direction: 'up' | 'down'): void {
  const day = getDayByIndex(dayIndex)
  if (!day) {
    return
  }

  const attractions = day.attractions
  if (direction === 'up' && attractionIndex > 0) {
    ;[attractions[attractionIndex - 1], attractions[attractionIndex]] = [
      attractions[attractionIndex],
      attractions[attractionIndex - 1]
    ]
  }

  if (direction === 'down' && attractionIndex < attractions.length - 1) {
    ;[attractions[attractionIndex + 1], attractions[attractionIndex]] = [
      attractions[attractionIndex],
      attractions[attractionIndex + 1]
    ]
  }
}

function buildMapCenter(): [number, number] {
  const firstAttraction = tripPlan.value?.days
    .flatMap((day) => day.attractions)
    .find((attraction) => attraction.location)

  if (firstAttraction?.location) {
    return [
      firstAttraction.location.longitude,
      firstAttraction.location.latitude
    ]
  }

  return [116.397128, 39.916527]
}

function drawRoutes(AMap: any, attractions: Array<Attraction & { dayIndex: number }>): void {
  const groups = attractions.reduce<Record<number, Array<Attraction & { dayIndex: number }>>>(
    (accumulator, attraction) => {
      if (!accumulator[attraction.dayIndex]) {
        accumulator[attraction.dayIndex] = []
      }
      accumulator[attraction.dayIndex].push(attraction)
      return accumulator
    },
    {}
  )

  Object.values(groups).forEach((dayAttractions) => {
    if (dayAttractions.length < 2 || !map) {
      return
    }

    const polyline = new AMap.Polyline({
      path: dayAttractions.map((attraction) => [
        attraction.location.longitude,
        attraction.location.latitude
      ]),
      strokeColor: '#2f6f55',
      strokeWeight: 4,
      strokeOpacity: 0.82,
      showDir: true
    })

    map.add(polyline)
  })
}

function addAttractionMarkers(AMap: any): void {
  if (!tripPlan.value || !map) {
    return
  }

  const attractions = tripPlan.value.days.flatMap((day) =>
    day.attractions
      .filter((attraction) => attraction.location?.longitude && attraction.location?.latitude)
      .map((attraction) => ({
        ...attraction,
        dayIndex: day.day_index
      }))
  )

  const markers = attractions.map((attraction, index) => {
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      label: {
        content: `<div style="padding: 6px 10px; border-radius: 999px; background: #2f6f55; color: #fffdf8; font-size: 12px; font-weight: 700;">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -34)
      }
    })

    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding: 12px 14px; max-width: 240px;">
          <strong style="font-size: 16px; color: #214c3b;">${attraction.name}</strong>
          <p style="margin: 8px 0 0; color: #46554f;">${attraction.address}</p>
          <p style="margin: 6px 0 0; color: #5f7067;">建议游览 ${attraction.visit_duration} 分钟</p>
          <p style="margin: 6px 0 0; color: #2f6f55;">第 ${attraction.dayIndex + 1} 天</p>
        </div>
      `,
      offset: new AMap.Pixel(0, -24)
    })

    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition())
    })

    return marker
  })

  if (markers.length > 0) {
    map.add(markers)
    map.setFitView(markers)
    drawRoutes(AMap, attractions)
  }
}

async function initMap(): Promise<void> {
  if (!tripPlan.value) {
    return
  }

  resetMap()

  if (!hasMapConfig.value) {
    mapError.value = ''
    return
  }

  try {
    window._AMapSecurityConfig = {
      securityJsCode: import.meta.env.VITE_AMAP_SECURITY_JS_CODE as string
    }

    const { default: AMapLoader } = await import('@amap/amap-jsapi-loader')
    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_API_KEY as string,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    map = new AMap.Map('amap-container', {
      zoom: 12,
      center: buildMapCenter(),
      viewMode: '3D'
    })

    addAttractionMarkers(AMap)
    mapError.value = ''
  } catch (error) {
    mapError.value = '地图暂时无法加载，你仍然可以浏览和编辑文字版行程。'
    console.error(error)
  }
}

async function handleExportClick({ key }: { key: string }): Promise<void> {
  const target = document.getElementById('result-export-target')
  if (!target || !tripPlan.value) {
    message.error('未找到可导出的行程内容')
    return
  }

  try {
    if (key === 'image') {
      message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })
      await exportElementAsImage(target, `旅行计划_${tripPlan.value.city}_${Date.now()}.png`)
      message.success({ content: '图片导出成功', key: 'export' })
      return
    }

    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })
    await exportElementAsPdf(target, `旅行计划_${tripPlan.value.city}_${Date.now()}.pdf`)
    message.success({ content: 'PDF导出成功', key: 'export' })
  } catch (error) {
    message.error({
      content: error instanceof Error ? error.message : '导出失败，请稍后重试',
      key: 'export'
    })
  }
}

onMounted(() => {
  void loadTripPlan()
})

onBeforeUnmount(() => {
  resetMap()
})
</script>

<style scoped>
.result-view {
  display: grid;
  gap: 22px;
  max-width: 1360px;
  margin: 0 auto;
}

.result-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px 28px;
}

.header-copy {
  max-width: 760px;
}

.result-title {
  margin: 10px 0 8px;
  font-family: var(--font-display);
  font-size: clamp(2.1rem, 4vw, 3.4rem);
  color: var(--color-primary-deep);
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

.result-layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.result-side-nav {
  position: relative;
}

.result-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.top-overview {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 20px;
}

.top-left-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.overview-pill {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(47, 111, 85, 0.08);
  color: var(--color-primary-deep);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.overview-grid {
  display: grid;
  gap: 16px;
}

.overview-item {
  padding: 18px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.78), rgba(247, 240, 227, 0.72));
}

.overview-item p,
.overview-item strong {
  display: block;
  margin-top: 8px;
  color: var(--color-text);
  line-height: 1.8;
}

.overview-label {
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.budget-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.budget-stat {
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(47, 111, 85, 0.08);
}

.budget-stat span {
  display: block;
  color: var(--color-text-muted);
  font-size: 13px;
}

.budget-stat strong {
  display: block;
  margin-top: 10px;
  color: var(--color-primary-deep);
  font-size: 1.5rem;
}

.budget-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 18px 20px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary) 0%, #4a896d 100%);
  color: #fffdf8;
}

.budget-total strong {
  font-size: 1.9rem;
  font-family: var(--font-display);
}

.map-card {
  min-height: 100%;
}

.map-surface,
.map-fallback {
  min-height: 520px;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.map-surface {
  background: linear-gradient(135deg, rgba(240, 245, 239, 0.7), rgba(225, 236, 229, 0.8));
}

.map-fallback {
  display: grid;
  align-content: center;
  justify-items: start;
  gap: 8px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(61, 132, 147, 0.12), transparent 26%),
    linear-gradient(160deg, rgba(255, 255, 255, 0.78), rgba(239, 230, 212, 0.84));
  border: 1px dashed rgba(47, 111, 85, 0.24);
}

.map-fallback span {
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.map-fallback strong {
  font-family: var(--font-display);
  font-size: 1.7rem;
  color: var(--color-primary-deep);
}

.map-fallback p,
.map-error {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
}

.map-error {
  margin-top: 12px;
}

.day-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
}

.day-panel-header div {
  display: grid;
  gap: 4px;
}

.day-panel-header strong {
  color: var(--color-primary-deep);
}

.day-panel-header span,
.day-panel-header small {
  color: var(--color-text-muted);
}

.day-anchor {
  position: relative;
  top: -90px;
  height: 0;
}

.day-summary-panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.day-summary-item {
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(247, 241, 230, 0.76);
}

.day-summary-item span {
  display: block;
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.day-summary-item strong {
  display: block;
  margin-top: 10px;
  line-height: 1.7;
}

.attraction-card :deep(.ant-card-body) {
  padding-top: 14px;
}

.attraction-media {
  position: relative;
  margin-bottom: 14px;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.attraction-image {
  display: block;
  width: 100%;
  height: 220px;
  object-fit: cover;
}

.attraction-image-empty {
  display: grid;
  align-content: end;
  gap: 8px;
  width: 100%;
  min-height: 220px;
  padding: 20px;
  background:
    radial-gradient(circle at top right, rgba(93, 157, 125, 0.18), transparent 24%),
    linear-gradient(160deg, rgba(250, 247, 240, 0.96), rgba(233, 225, 208, 0.94));
}

.attraction-image-empty strong {
  color: var(--color-primary-deep);
  font-family: var(--font-display);
  font-size: 1.5rem;
}

.attraction-image-empty p {
  margin: 0;
  color: var(--color-text-muted);
}

.attraction-empty-kicker {
  color: var(--color-text-soft);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.attraction-order {
  position: absolute;
  top: 14px;
  padding: 8px 12px;
  border-radius: 999px;
  color: #fffdf8;
  font-weight: 700;
}

.attraction-order {
  left: 14px;
  background: rgba(33, 76, 59, 0.92);
}

.attraction-edit-fields {
  display: grid;
  gap: 12px;
}

.field-label {
  display: grid;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 600;
}

.attraction-meta {
  color: var(--color-text-muted);
  line-height: 1.8;
}

.attraction-meta p {
  margin: 0 0 8px;
}

.hotel-card {
  display: grid;
  gap: 18px;
  padding: 22px;
  background:
    radial-gradient(circle at top right, rgba(217, 126, 51, 0.1), transparent 24%),
    linear-gradient(135deg, rgba(245, 241, 233, 0.95), rgba(233, 242, 236, 0.92)) !important;
}

.hotel-card-header {
  display: grid;
  gap: 8px;
}

.hotel-kicker {
  color: var(--color-text-soft);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hotel-name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--color-primary-deep);
}

.hotel-type {
  margin: 0;
  color: var(--color-text-muted);
}

.hotel-card-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.hotel-detail {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.6);
}

.hotel-detail span {
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hotel-detail strong {
  line-height: 1.7;
}

.meal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.meal-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  min-height: 180px;
  background:
    radial-gradient(circle at top left, rgba(217, 126, 51, 0.12), transparent 22%),
    linear-gradient(180deg, rgba(255, 252, 246, 0.92), rgba(244, 238, 226, 0.88)) !important;
}

.meal-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(47, 111, 85, 0.1);
  color: var(--color-primary-deep);
  font-size: 12px;
  font-weight: 700;
}

.meal-name {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-primary-deep);
}

.meal-description,
.meal-address {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.8;
}

.weather-card-shell :deep(.ant-card-body) {
  padding-top: 18px;
}

.weather-card {
  display: grid;
  gap: 12px;
  padding: 18px;
}

.weather-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text-muted);
}

.weather-wind {
  padding-top: 12px;
  border-top: 1px solid rgba(47, 111, 85, 0.1);
}

.empty-copy {
  color: var(--color-text-muted);
}

.back-top-button {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
  color: #fffdf8;
  box-shadow: var(--shadow-strong);
  font-size: 24px;
}

@media (max-width: 1100px) {
  .result-layout,
  .top-overview {
    grid-template-columns: 1fr;
  }

  .result-side-nav {
    display: none;
  }
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
    align-items: flex-start;
    padding: 22px 20px;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .budget-grid,
  .day-summary-panel,
  .hotel-card-body,
  .meal-grid {
    grid-template-columns: 1fr;
  }

  .map-surface,
  .map-fallback {
    min-height: 340px;
  }
}
</style>
