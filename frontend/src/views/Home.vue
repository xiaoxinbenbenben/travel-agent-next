<template>
  <div class="home-view fade-rise">
    <section class="hero-section">
      <div class="hero-copy">
        <span class="section-kicker">Journey Composer</span>
        <h2 class="headline">把一次出行，整理成一张有温度的旅行地图</h2>
        <p class="supporting-text">
          输入目的地、日期与偏好，我们会把景点、天气、住宿和预算建议整理成一份可继续编辑的旅程草案，
          让准备出发这件事变得更轻松，也更有画面感。
        </p>

        <div class="hero-metrics">
          <div class="metric-card glass-panel">
            <span class="metric-value">AI</span>
            <span class="metric-label">从景点、住宿到天气联动整理</span>
          </div>
          <div class="metric-card glass-panel">
            <span class="metric-value">30</span>
            <span class="metric-label">最长支持 30 天旅程</span>
          </div>
          <div class="metric-card glass-panel">
            <span class="metric-value">Plan</span>
            <span class="metric-label">生成后仍可继续微调和导出</span>
          </div>
        </div>
      </div>

      <div class="hero-aside glass-panel">
        <p class="hero-aside-title">这一程将为你整理</p>
        <ul class="hero-list">
          <li>按天展开的景点路线与浏览节奏</li>
          <li>住宿、餐饮、天气与预算参考</li>
          <li>可继续编辑与导出的旅行草案</li>
        </ul>
        <div class="hero-badges">
          <span>自然探索</span>
          <span>城市漫游</span>
          <span>轻松规划</span>
        </div>
      </div>
    </section>

    <a-card class="form-card" :bordered="false">
      <div class="form-title-row">
        <div>
          <span class="section-kicker">Trip Brief</span>
          <h3 class="form-title">出发前信息卡</h3>
        </div>
        <div class="day-summary glass-panel">
          <span class="day-summary-label">预计旅程长度</span>
          <span class="day-summary-value">{{ formData.travel_days }} 天</span>
        </div>
      </div>

      <a-form
        :model="formData"
        layout="vertical"
        @finish="handleSubmit"
      >
        <section class="form-section">
          <div class="section-header">
            <div class="section-number">01</div>
            <div>
              <h4 class="section-title">目的地与日期</h4>
              <p class="section-description">先确定城市与出发时间，这是后续景点、天气和住宿推荐的基础。</p>
            </div>
          </div>

          <a-row :gutter="[18, 18]">
            <a-col :xs="24" :md="9">
              <a-form-item
                name="city"
                :rules="[{ required: true, message: '请输入目的地城市' }]"
                label="目的地城市"
              >
                <a-input
                  v-model:value="formData.city"
                  data-testid="city-input"
                  placeholder="例如：杭州"
                  size="large"
                >
                  <template #prefix>🏞️</template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-form-item
                name="start_date"
                :rules="[{ required: true, message: '请选择开始日期' }]"
                label="开始日期"
              >
                <div data-testid="start-date-picker" class="date-input-shell">
                  <a-input
                    v-model:value="formData.start_date"
                    type="date"
                    size="large"
                  />
                </div>
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-form-item
                name="end_date"
                :rules="[{ required: true, message: '请选择结束日期' }]"
                label="结束日期"
              >
                <div data-testid="end-date-picker" class="date-input-shell">
                  <a-input
                    v-model:value="formData.end_date"
                    type="date"
                    size="large"
                  />
                </div>
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="3">
              <a-form-item label="旅行天数">
                <div class="days-badge">
                  <span>{{ formData.travel_days }}</span>
                  <small>days</small>
                </div>
              </a-form-item>
            </a-col>
          </a-row>
        </section>

        <section class="form-section">
          <div class="section-header">
            <div class="section-number">02</div>
            <div>
              <h4 class="section-title">偏好设置</h4>
              <p class="section-description">从交通、住宿到兴趣方向，先把这趟旅程的气质定下来。</p>
            </div>
          </div>

          <a-row :gutter="[18, 18]">
            <a-col :xs="24" :md="8">
              <a-form-item name="transportation" label="交通方式">
                <a-select v-model:value="formData.transportation" size="large">
                  <a-select-option
                    v-for="option in transportationOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.emoji }} {{ option.label }} · {{ option.detail }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="8">
              <a-form-item name="accommodation" label="住宿偏好">
                <a-select v-model:value="formData.accommodation" size="large">
                  <a-select-option
                    v-for="option in accommodationOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.emoji }} {{ option.label }} · {{ option.detail }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="8">
              <a-form-item name="preferences" label="旅行偏好">
                <a-checkbox-group v-model:value="formData.preferences" class="preference-grid">
                  <a-checkbox
                    v-for="option in preferenceOptions"
                    :key="option.value"
                    :value="option.value"
                    class="preference-chip"
                  >
                    {{ option.emoji }} {{ option.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </a-form-item>
            </a-col>
          </a-row>
        </section>

        <section class="form-section">
          <div class="section-header">
            <div class="section-number">03</div>
            <div>
              <h4 class="section-title">额外要求</h4>
              <p class="section-description">这里适合写节奏、预算、餐饮忌口、无障碍需求，或者你特别想去的地点。</p>
            </div>
          </div>

          <a-form-item name="free_text_input" label="自由补充">
            <a-textarea
              v-model:value="formData.free_text_input"
              data-testid="free-text-input"
              :rows="4"
              placeholder="例如：想安排一次日落观景；需要尽量减少上下坡；希望晚餐更偏本地菜。"
            />
          </a-form-item>
        </section>

        <div class="submit-area">
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            class="submit-button"
            :loading="loading"
            data-testid="submit-trip-button"
          >
            <template v-if="loading">
              正在生成旅行计划...
            </template>
            <template v-else>
              开始规划我的旅行
            </template>
          </a-button>

          <div v-if="loading" class="loading-panel glass-panel">
            <a-progress
              :percent="loadingProgress"
              status="active"
              :stroke-color="{
                '0%': '#2f6f55',
                '100%': '#d97e33'
              }"
              :stroke-width="10"
            />
            <p class="loading-copy">{{ loadingStatus }}</p>
          </div>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import {
  ACCOMMODATION_OPTIONS,
  LOADING_PHASES,
  PREFERENCE_OPTIONS,
  TRANSPORTATION_OPTIONS
} from '@/constants/trip'
import { generateTripPlan } from '@/services/api'
import type { TripFormData } from '@/types'
import { calculateTravelDays, isValidDateRange } from '@/utils/date'

interface HomeFormState extends TripFormData {}

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const transportationOptions = TRANSPORTATION_OPTIONS
const accommodationOptions = ACCOMMODATION_OPTIONS
const preferenceOptions = PREFERENCE_OPTIONS

const formData = reactive<HomeFormState>({
  city: '',
  start_date: '',
  end_date: '',
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: ''
})

let progressTimer: number | null = null

function clearProgressTimer(): void {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer)
    progressTimer = null
  }
}

function startProgress(): void {
  loadingProgress.value = 0
  loadingStatus.value = LOADING_PHASES[0]

  progressTimer = window.setInterval(() => {
    if (loadingProgress.value >= 90) {
      return
    }

    loadingProgress.value = Math.min(loadingProgress.value + 14, 90)
    const phaseIndex = Math.min(
      Math.floor(loadingProgress.value / 28),
      LOADING_PHASES.length - 1
    )
    loadingStatus.value = LOADING_PHASES[phaseIndex]
  }, 520)
}

watch(
  () => [formData.start_date, formData.end_date] as const,
  ([startDate, endDate]) => {
    if (!startDate || !endDate) {
      return
    }

    const days = calculateTravelDays(startDate, endDate)
    if (days === null) {
      return
    }

    if (!isValidDateRange(days)) {
      if (days <= 0) {
        message.warning('结束日期不能早于开始日期')
      } else {
        message.warning('旅行天数不能超过 30 天')
      }
      formData.end_date = ''
      return
    }

    formData.travel_days = days
  }
)

async function handleSubmit(): Promise<void> {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择完整的出行日期')
    return
  }

  loading.value = true
  startProgress()

  try {
    const response = await generateTripPlan({
      ...formData
    })

    clearProgressTimer()
    loadingProgress.value = 100
    loadingStatus.value = '行程已经整理完成，正在展开结果页...'

    if (!response.success || !response.data) {
      message.error(response.message || '生成失败，请稍后重试')
      return
    }

    sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
    message.success('旅行计划生成成功')

    window.setTimeout(() => {
      void router.push('/result')
    }, 420)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '生成旅行计划失败，请稍后重试')
  } finally {
    window.setTimeout(() => {
      clearProgressTimer()
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 960)
  }
}

onBeforeUnmount(() => {
  clearProgressTimer()
})
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1360px;
  margin: 0 auto;
}

.hero-section {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  gap: 20px;
  align-items: stretch;
}

.hero-copy,
.hero-aside,
.form-card {
  overflow: hidden;
}

.hero-copy {
  position: relative;
  padding: 40px;
  border-radius: var(--radius-xl);
  background:
    linear-gradient(135deg, rgba(255, 253, 247, 0.9), rgba(241, 235, 224, 0.86)),
    radial-gradient(circle at right top, rgba(47, 111, 85, 0.12), transparent 35%);
  border: 1px solid rgba(47, 111, 85, 0.12);
  box-shadow: var(--shadow-card);
}

.hero-copy::after {
  content: '';
  position: absolute;
  inset: auto -40px -60px auto;
  width: 280px;
  height: 180px;
  background:
    radial-gradient(circle, rgba(217, 126, 51, 0.18), transparent 58%),
    radial-gradient(circle at left top, rgba(61, 132, 147, 0.18), transparent 48%);
  pointer-events: none;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px;
}

.metric-value {
  color: var(--color-primary-deep);
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 2.3vw, 2rem);
}

.metric-label {
  color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1.6;
}

.hero-aside {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 22px;
  padding: 28px;
}

.hero-aside-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.6rem;
  color: var(--color-primary-deep);
}

.hero-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-muted);
  line-height: 1.8;
}

.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-badges span {
  display: inline-flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(47, 111, 85, 0.08);
  color: var(--color-primary-deep);
  font-size: 13px;
  font-weight: 700;
}

.form-card {
  padding: 10px;
}

.form-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.form-title {
  margin: 10px 0 0;
  font-family: var(--font-display);
  font-size: 2rem;
  color: var(--color-primary-deep);
}

.day-summary {
  min-width: 180px;
  padding: 16px 20px;
  text-align: right;
}

.day-summary-label {
  display: block;
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.day-summary-value {
  display: block;
  margin-top: 6px;
  color: var(--color-primary-deep);
  font-family: var(--font-display);
  font-size: 2rem;
}

.form-section {
  padding: 24px 0;
  border-top: 1px solid rgba(47, 111, 85, 0.08);
}

.form-section:first-of-type {
  border-top: none;
}

.section-header {
  display: flex;
  gap: 18px;
  margin-bottom: 18px;
}

.section-number {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--color-primary) 0%, #4e8e71 100%);
  color: #fffdf8;
  font-family: var(--font-display);
  font-size: 1.2rem;
}

.section-title {
  margin: 0 0 6px;
  color: var(--color-primary-deep);
  font-size: 1.15rem;
}

.section-description {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
}

.days-badge {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  min-height: 54px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(47, 111, 85, 0.12), rgba(217, 126, 51, 0.12));
  color: var(--color-primary-deep);
  font-family: var(--font-display);
  font-size: 2rem;
}

.days-badge small {
  color: var(--color-text-soft);
  font-family: var(--font-body);
  font-size: 13px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.date-input-shell :deep(.ant-input) {
  min-height: 58px;
  padding-inline: 16px;
  border-radius: 18px;
  font-size: 16px;
}

.date-input-shell :deep(input[type='date']::-webkit-calendar-picker-indicator) {
  transform: scale(1.15);
  cursor: pointer;
}

.preference-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.preference-chip {
  display: flex;
  align-items: center;
  min-height: 48px;
  margin-inline-start: 0;
  padding: 0 14px;
  border: 1px solid rgba(47, 111, 85, 0.14);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.68);
}

.submit-area {
  display: grid;
  gap: 18px;
  padding-top: 12px;
}

.submit-button {
  min-height: 58px;
  font-size: 16px;
  letter-spacing: 0.03em;
}

.loading-panel {
  padding: 18px 20px;
}

.loading-copy {
  margin: 12px 0 0;
  color: var(--color-text-muted);
}

@media (max-width: 1080px) {
  .hero-section {
    grid-template-columns: 1fr;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-copy,
  .hero-aside {
    padding: 24px;
  }

  .form-title-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .day-summary {
    width: 100%;
    text-align: left;
  }

  .preference-grid {
    grid-template-columns: 1fr;
  }
}
</style>
