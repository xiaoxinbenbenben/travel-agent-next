<template>
  <a-layout class="app-layout">
    <div class="app-backdrop">
      <span class="terrain terrain-left"></span>
      <span class="terrain terrain-right"></span>
      <span class="terrain terrain-bottom"></span>
    </div>

    <a-layout-header class="app-header">
      <div class="brand-shell glass-panel">
        <RouterLink to="/" class="brand-link">
          <div class="brand-emblem">
            <span class="brand-ring"></span>
            <span class="brand-core"></span>
          </div>
          <div>
            <p class="brand-kicker">travel-agent-next</p>
            <h1 class="brand-title">自然探索旅行助手</h1>
          </div>
        </RouterLink>

        <div class="brand-status">
          <span class="status-label">{{ pageLabel }}</span>
          <span class="status-copy">为下一段旅程整理景点、节奏与灵感</span>
        </div>
      </div>
    </a-layout-header>

    <a-layout-content class="app-content page-shell">
      <RouterView />
    </a-layout-content>

    <a-layout-footer class="app-footer">
      <span>Travel Agent Next Frontend</span>
      <span>Vue3 + TypeScript + Ant Design Vue</span>
      <span>景点 · 地图 · 天气 · 预算</span>
    </a-layout-footer>
  </a-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()

const pageLabel = computed(() => {
  if (route.name === 'Result') {
    return '查看并编辑旅行结果'
  }
  return '创建一次新的探索旅程'
})
</script>

<style scoped>
.app-layout {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.app-backdrop {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.terrain {
  position: absolute;
  border-radius: 999px;
  filter: blur(18px);
  opacity: 0.45;
}

.terrain-left {
  top: 68px;
  left: -120px;
  width: 340px;
  height: 340px;
  background: radial-gradient(circle, rgba(93, 157, 125, 0.28), transparent 68%);
}

.terrain-right {
  top: 140px;
  right: -80px;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(64, 132, 156, 0.22), transparent 68%);
}

.terrain-bottom {
  right: 15%;
  bottom: -140px;
  width: 420px;
  height: 280px;
  background: radial-gradient(circle, rgba(219, 126, 51, 0.16), transparent 70%);
}

.app-header {
  height: auto;
  padding: 20px 24px 0;
  background: transparent;
  line-height: normal;
}

.brand-shell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  max-width: 1360px;
  margin: 0 auto;
  padding: 18px 24px;
}

.brand-link {
  display: inline-flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
}

.brand-emblem {
  position: relative;
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
}

.brand-ring,
.brand-core {
  position: absolute;
  border-radius: 50%;
}

.brand-ring {
  inset: 0;
  border: 1px solid rgba(47, 111, 85, 0.26);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(219, 234, 223, 0.74));
}

.brand-core {
  inset: 15px;
  background: linear-gradient(135deg, #2f6f55 0%, #7ab595 100%);
  box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.38);
}

.brand-kicker {
  margin: 0 0 6px;
  color: var(--color-text-soft);
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.brand-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.4rem, 3vw, 2rem);
  color: var(--color-primary-deep);
}

.brand-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  text-align: right;
}

.status-label {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(47, 111, 85, 0.1);
  color: var(--color-primary-deep);
  font-weight: 700;
}

.status-copy {
  color: var(--color-text-muted);
  font-size: 14px;
}

.app-content {
  padding: 24px 24px 48px;
}

.app-footer {
  display: flex;
  justify-content: center;
  gap: 18px;
  padding: 0 24px 28px;
  color: var(--color-text-soft);
  text-align: center;
  font-size: 13px;
}

@media (max-width: 960px) {
  .brand-shell {
    flex-direction: column;
    align-items: flex-start;
  }

  .brand-status {
    align-items: flex-start;
    text-align: left;
  }

  .app-footer {
    flex-direction: column;
    gap: 8px;
  }
}

@media (max-width: 640px) {
  .app-header,
  .app-content {
    padding-left: 14px;
    padding-right: 14px;
  }

  .brand-shell {
    padding: 16px;
  }
}
</style>
