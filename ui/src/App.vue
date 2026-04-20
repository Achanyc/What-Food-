<template>
  <div id="app" class="app-root">
    <!-- 顶栏：品牌 + 辅助说明 -->
    <header class="top-bar">
      <div class="top-bar-inner">
        <div class="brand">
          <span class="brand-logo" aria-hidden="true">🍜</span>
          <div class="brand-text">
            <h1>AiMenu 智能点餐</h1>
            <p class="brand-sub">语音级的理解 · 到店级的推荐 · 一键查配送</p>
          </div>
        </div>
        <div class="top-bar-tags">
          <span class="pill pill-warm">今日营业</span>
          <span class="pill pill-muted">AI 点餐助手在线</span>
        </div>
      </div>
    </header>

    <main class="page-main">
      <!-- 主内容：左侧对话 + 右侧菜单（大屏并排） -->
      <div class="layout-grid">
        <!-- 智能对话 -->
        <section class="surface chat-surface" aria-labelledby="chat-title">
          <div class="surface-head">
            <h2 id="chat-title" class="surface-title">
              <span class="title-icon">💬</span>
              智能点餐助手
            </h2>
            <p class="surface-desc">描述口味、菜系、忌口或用餐场景，我来帮您推荐</p>
          </div>

          <div ref="chatScrollRef" class="chat-thread">
            <div v-if="chatMessages.length === 0 && !chatLoading" class="chat-empty">
              <p class="chat-empty-title">试试这样说</p>
              <ul class="hint-chips">
                <li v-for="(hint, idx) in quickHints" :key="idx">
                  <button type="button" class="hint-btn" @click="applyHint(hint)">{{ hint }}</button>
                </li>
              </ul>
            </div>

            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              class="msg-row"
              :class="msg.role === 'user' ? 'msg-row-user' : 'msg-row-bot'"
            >
              <div class="msg-meta">
                {{ msg.role === 'user' ? '我' : '点餐助手' }}
              </div>
              <div
                class="msg-bubble"
                :class="msg.role === 'user' ? 'bubble-user' : 'bubble-bot'"
              >
                <template v-if="msg.role === 'user'">{{ msg.content }}</template>
                <div v-else class="formatted-content" v-html="formatMarkdown(msg.content)" />
              </div>
            </div>

            <div v-if="chatLoading" class="msg-row msg-row-bot typing-row">
              <div class="msg-meta">点餐助手</div>
              <div class="bubble-bot typing-bubble">
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-text">正在为您思考…</span>
              </div>
            </div>
          </div>

          <div class="composer">
            <el-input
              v-model="chatQuery"
              type="textarea"
              :rows="3"
              placeholder="例如：推荐不太辣的川菜、两人套餐、清淡一点的汤…"
              class="composer-input"
              resize="none"
              @keydown.ctrl.enter="sendChatQuery"
              @keydown.meta.enter="sendChatQuery"
            />
            <div class="composer-actions">
              <span class="composer-tip">Ctrl / ⌘ + Enter 快速发送</span>
              <el-button
                type="primary"
                class="composer-send"
                round
                @click="sendChatQuery"
                :loading="chatLoading"
                :disabled="chatLoading || !chatQuery.trim()"
              >
                {{ chatLoading ? '生成中…' : '发送' }}
              </el-button>
            </div>
          </div>
        </section>

        <!-- 本店菜单 -->
        <section id="menu-anchor" class="surface menu-surface" aria-labelledby="menu-title">
          <div class="surface-head surface-head-row">
            <div>
              <h2 id="menu-title" class="surface-title">
                <span class="title-icon">📋</span>
                本店菜单
              </h2>
              <p class="surface-desc">选好菜后可在左侧继续追问搭配与口味</p>
            </div>
            <el-button type="primary" plain round size="small" @click="loadMenuItems" :loading="menuLoading">
              刷新菜单
            </el-button>
          </div>

          <div v-if="menuItems.length > 0" class="menu-grid">
            <article
              v-for="item in menuItems"
              :key="item.id"
              class="menu-card"
              :class="{ 'menu-card--hot': highlightedItems.includes(item.id.toString()) }"
            >
              <div class="menu-card-head">
                <h3>{{ item.dish_name }}</h3>
                <span class="menu-price">{{ item.formatted_price }}</span>
              </div>
              <p class="menu-desc">{{ item.description }}</p>
              <div class="menu-tags">
                <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                <el-tag size="small" :type="getSpiceType(item.spice_level)" effect="light">
                  {{ item.spice_text }}
                </el-tag>
                <el-tag v-if="item.is_vegetarian" size="small" type="success" effect="plain">素食</el-tag>
                <el-tag v-if="highlightedItems.includes(item.id.toString())" size="small" type="danger" effect="dark">
                  AI 推荐
                </el-tag>
              </div>
            </article>
          </div>
          <div v-else-if="!menuLoading" class="menu-empty">
            <el-empty description="暂无菜品，请稍后刷新" />
          </div>
          <div v-if="menuLoading" class="menu-skeleton">
            <el-skeleton :rows="4" animated />
          </div>
        </section>
      </div>

      <!-- 配送查询：全宽横条 -->
      <section class="surface delivery-surface" aria-labelledby="delivery-title">
        <div class="surface-head surface-head-row">
          <div>
            <h2 id="delivery-title" class="surface-title">
              <span class="title-icon">📍</span>
              配送范围查询
            </h2>
            <p class="surface-desc">输入收货地址，查看是否在配送范围内（骑行 / 驾车 / 步行测算）</p>
          </div>
        </div>

        <div class="delivery-row">
          <el-input
            v-model="deliveryAddress"
            placeholder="请输入详细地址，例如：四川省南充市顺庆区××路××号"
            class="delivery-field"
            size="large"
            clearable
          />
          <el-select v-model="travelMode" placeholder="出行方式" class="delivery-mode" size="large">
            <el-option label="步行" value="1" />
            <el-option label="骑行" value="2" />
            <el-option label="驾车" value="3" />
          </el-select>
          <el-button type="primary" size="large" class="delivery-submit" round @click="checkDelivery" :loading="deliveryLoading">
            查询配送范围
          </el-button>
        </div>

        <div v-if="deliveryResponse" class="delivery-result">
          <el-alert
            :title="deliveryAlertTitle"
            :description="deliveryAlertDesc"
            :type="deliveryResponse.success === false ? 'error' : deliveryResponse.in_range ? 'success' : 'warning'"
            :closable="false"
            show-icon
          />
          <div v-if="deliveryResponse.success !== false" class="delivery-stats">
            <div class="stat">
              <span class="stat-label">测算方式</span>
              <span class="stat-value">{{ travelModeText(deliveryResponse.travel_mode) }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">直线距离约</span>
              <span class="stat-value stat-accent">{{ Number(deliveryResponse.distance || 0).toFixed(2) }} km</span>
            </div>
            <div class="stat">
              <span class="stat-label">预估耗时</span>
              <span class="stat-value">{{ deliveryDuration.minutes }}′{{ deliveryDuration.secondsPadded }}″</span>
            </div>
            <div v-if="deliveryResponse.formatted_address" class="stat stat-wide">
              <span class="stat-label">解析地址</span>
              <span class="stat-value stat-wrap">{{ deliveryResponse.formatted_address }}</span>
            </div>
          </div>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <span>AiMenu · 智能点餐演示 · 出品仅供学习交流</span>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { chatAPI, deliveryAPI, menuAPI } from './api/index.js'

export default {
  name: 'App',
  setup() {
    const chatQuery = ref('')
    const chatLoading = ref(false)
    const chatMessages = ref([])
    const chatScrollRef = ref(null)

    const quickHints = [
      '推荐川菜菜系',
      '不太辣的荤菜有哪些',
      '有没有清淡的汤',
      '两个人吃饭怎么搭配'
    ]

    const deliveryAddress = ref('')
    const travelMode = ref('2')
    const deliveryResponse = ref(null)
    const deliveryLoading = ref(false)

    const travelModeText = (mode) => {
      const map = { '1': '步行', '2': '骑行', '3': '驾车' }
      return map[String(mode)] || String(mode || '')
    }

    const deliveryDuration = computed(() => {
      const raw = deliveryResponse.value?.duration
      const totalSeconds = Math.max(0, Math.round(Number(raw || 0)))
      const minutes = Math.floor(totalSeconds / 60)
      const seconds = totalSeconds % 60
      return {
        minutes,
        seconds,
        secondsPadded: String(seconds).padStart(2, '0')
      }
    })

    const deliveryAlertTitle = computed(() => {
      const r = deliveryResponse.value
      if (!r) return ''
      if (r.success === false) return '暂时无法查询配送范围'
      return r.in_range ? '在配送范围内' : '超出当前配送范围'
    })

    const deliveryAlertDesc = computed(() => {
      const r = deliveryResponse.value
      if (!r) return ''
      if (r.success === false) return r.message || '请检查地址或稍后重试'
      return ''
    })

    const menuItems = ref([])
    const menuLoading = ref(false)
    const highlightedItems = ref([])

    function formatMarkdown(text) {
      if (!text) return ''
      return String(text)
        .replace(/#{1,6} (.*?)$/gm, (match, p1) => {
          const level = match.trim().split(' ')[0].length
          return `<h${level}>${p1}</h${level}>`
        })
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^- (.*?)$/gm, '<li>$1</li>')
        .replace(/(<li>.*?<\/li>)\n(<li>.*?<\/li>)/gs, '<ul>$1$2</ul>')
        .replace(/^\d+\. (.*?)$/gm, '<li>$1</li>')
        .replace(/\n\n(.*?)\n\n/gs, '<p>$1</p>')
        .replace(/\n/g, '<br/>')
    }

    const scrollChatToBottom = () => {
      nextTick(() => {
        const el = chatScrollRef.value
        if (el) el.scrollTop = el.scrollHeight
      })
    }

    watch(chatMessages, () => scrollChatToBottom(), { deep: true })
    watch(chatLoading, (v) => {
      if (v) scrollChatToBottom()
    })

    const applyHint = (text) => {
      chatQuery.value = text
    }

    const highlightRecommendedItems = (menuIds) => {
      if (!menuIds || !Array.isArray(menuIds) || menuIds.length === 0) {
        highlightedItems.value = []
        return
      }
      highlightedItems.value = menuIds.map((id) => id.toString())
      if (menuItems.value.length === 0) loadMenuItems()
      setTimeout(() => {
        document.getElementById('menu-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 320)
    }

    const sendChatQuery = async () => {
      const q = chatQuery.value.trim()
      if (!q) return

      chatLoading.value = true
      chatMessages.value.push({ role: 'user', content: q })

      try {
        const response = await chatAPI.sendMessage(q)

        let assistantText =
          response.recommendation ||
          response.recommdation ||
          response.response ||
          ''

        if (
          assistantText &&
          typeof assistantText === 'object' &&
          assistantText !== null &&
          !Array.isArray(assistantText)
        ) {
          assistantText = JSON.stringify(assistantText)
        }

        if (!assistantText) {
          assistantText = '抱歉，暂时无法理解您的问题，请换一种说法试试。'
        }

        chatMessages.value.push({ role: 'assistant', content: assistantText })

        if (response.menu_ids && response.menu_ids.length) {
          highlightRecommendedItems(response.menu_ids)
        } else {
          highlightedItems.value = []
        }
      } catch (error) {
        const errMsg =
          error?.message ||
          error?.response?.data?.detail ||
          '请求失败，请确认后端已启动或稍后重试。'
        chatMessages.value.push({
          role: 'assistant',
          content: `⚠️ ${errMsg}`
        })
      } finally {
        chatLoading.value = false
      }
    }

    const checkDelivery = async () => {
      if (!deliveryAddress.value.trim()) return
      deliveryLoading.value = true
      try {
        deliveryResponse.value = await deliveryAPI.checkRange(deliveryAddress.value, travelMode.value)
      } catch (error) {
        deliveryResponse.value = {
          success: false,
          in_range: false,
          message: error?.message || '查询失败，请稍后再试',
          distance: 0
        }
      } finally {
        deliveryLoading.value = false
      }
    }

    const loadMenuItems = async () => {
      menuLoading.value = true
      try {
        const response = await menuAPI.getMenuList()
        menuItems.value = response.menu_items || []
      } catch (error) {
        console.error('加载菜品失败:', error)
        menuItems.value = []
      } finally {
        menuLoading.value = false
      }
    }

    const getSpiceType = (level) => {
      const types = ['', 'success', 'warning', 'danger']
      return types[level] || ''
    }

    onMounted(() => loadMenuItems())

    return {
      chatQuery,
      chatLoading,
      chatMessages,
      chatScrollRef,
      quickHints,
      applyHint,
      formatMarkdown,
      deliveryAddress,
      travelMode,
      deliveryResponse,
      deliveryLoading,
      travelModeText,
      deliveryDuration,
      deliveryAlertTitle,
      deliveryAlertDesc,
      menuItems,
      menuLoading,
      highlightedItems,
      sendChatQuery,
      checkDelivery,
      loadMenuItems,
      getSpiceType
    }
  }
}
</script>

<style>
/* ========== 设计变量（外卖平台常见暖色 + 卡片层级） ========== */
.app-root {
  --color-bg: #f7f5f2;
  --color-surface: #ffffff;
  --color-text: #1a1a1a;
  --color-muted: #6b6560;
  --color-accent: #ff6b35;
  --color-accent-soft: rgba(255, 107, 53, 0.12);
  --color-border: rgba(0, 0, 0, 0.06);
  --shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 12px 40px rgba(15, 23, 42, 0.08);
  --radius-lg: 16px;
  --radius-md: 12px;
  --font-sans: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;

  min-height: 100vh;
  background: linear-gradient(180deg, #fff9f5 0%, var(--color-bg) 38%, #eef1f5 100%);
  color: var(--color-text);
  font-family: var(--font-sans);
}

#app {
  min-height: 100vh;
}

/* 顶栏 */
.top-bar {
  background: linear-gradient(135deg, #ff8a5c 0%, #ff6b35 48%, #e85d2a 100%);
  color: #fff;
  padding: 18px 24px 22px;
  box-shadow: var(--shadow-md);
}

.top-bar-inner {
  max-width: 1180px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  font-size: 2.25rem;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.15));
}

.brand-text h1 {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.brand-sub {
  margin: 4px 0 0;
  font-size: 0.85rem;
  opacity: 0.92;
}

.top-bar-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.pill-warm {
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.pill-muted {
  background: rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* 主布局 */
.page-main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.layout-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 960px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }
}

.surface {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.surface-head {
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(180deg, #fffdfb 0%, #fff 100%);
}

.surface-head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.surface-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 1.15rem;
}

.surface-desc {
  margin: 6px 0 0;
  font-size: 0.8rem;
  color: var(--color-muted);
  line-height: 1.45;
}

/* 对话区 */
.chat-surface {
  display: flex;
  flex-direction: column;
  min-height: 520px;
  max-height: min(78vh, 720px);
}

.chat-thread {
  flex: 1;
  overflow-y: auto;
  padding: 16px 18px;
  scroll-behavior: smooth;
  background: linear-gradient(180deg, #faf8f6 0%, #f3f1ee 100%);
}

.chat-empty {
  padding: 12px 4px 8px;
}

.chat-empty-title {
  font-size: 0.8rem;
  color: var(--color-muted);
  margin: 0 0 10px;
}

.hint-chips {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hint-btn {
  border: 1px dashed rgba(255, 107, 53, 0.45);
  background: #fff;
  color: #c2410c;
  font-size: 0.8rem;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.hint-btn:hover {
  background: var(--color-accent-soft);
  border-style: solid;
}

.msg-row {
  margin-bottom: 14px;
  max-width: 100%;
}

.msg-row-user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-row-bot {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.msg-meta {
  font-size: 0.7rem;
  color: var(--color-muted);
  margin-bottom: 4px;
  padding: 0 4px;
}

.msg-bubble {
  max-width: min(100%, 520px);
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 0.92rem;
  line-height: 1.65;
  word-break: break-word;
}

.bubble-user {
  background: linear-gradient(135deg, #ff6b35 0%, #ff8f65 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(255, 107, 53, 0.28);
}

.bubble-bot {
  background: #fff;
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
  box-shadow: var(--shadow-sm);
}

.typing-bubble {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.85rem;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: bounce 1.2s infinite ease-in-out both;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0.65);
    opacity: 0.45;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  margin-left: 6px;
  color: var(--color-muted);
}

/* 输入区 */
.composer {
  padding: 14px 16px 16px;
  border-top: 1px solid var(--color-border);
  background: #fff;
}

.composer-input :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  font-size: 0.92rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer-input :deep(.el-textarea__inner:focus) {
  border-color: rgba(255, 107, 53, 0.55);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 12px;
  flex-wrap: wrap;
}

.composer-tip {
  font-size: 0.72rem;
  color: var(--color-muted);
}

.composer-send {
  min-width: 112px;
  font-weight: 600;
  background: linear-gradient(135deg, #ff6b35 0%, #ff8f65 100%) !important;
  border: none !important;
}

.composer-send:hover,
.composer-send:focus {
  filter: brightness(1.05);
}

/* 富文本 */
.formatted-content {
  width: 100%;
}

.formatted-content h1,
.formatted-content h2,
.formatted-content h3 {
  margin: 12px 0 8px;
  font-weight: 600;
  color: var(--color-text);
}

.formatted-content h2 {
  font-size: 1.1rem;
}

.formatted-content strong {
  color: #111;
}

.formatted-content ul,
.formatted-content ol {
  padding-left: 1.25em;
  margin: 6px 0;
}

/* 菜单 */
.menu-surface {
  min-height: 520px;
  max-height: min(78vh, 720px);
  display: flex;
  flex-direction: column;
}

.menu-grid {
  padding: 14px 16px 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.menu-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: 14px 14px 12px;
  background: #fff;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.menu-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.menu-card--hot {
  border-color: rgba(255, 107, 53, 0.55);
  background: linear-gradient(180deg, #fffefb 0%, #fff 100%);
  box-shadow: 0 0 0 1px rgba(255, 107, 53, 0.12);
}

.menu-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.menu-card-head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.35;
}

.menu-price {
  flex-shrink: 0;
  color: #e11d48;
  font-weight: 700;
  font-size: 1.05rem;
}

.menu-desc {
  margin: 0 0 10px;
  font-size: 0.82rem;
  color: var(--color-muted);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.menu-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.menu-empty,
.menu-skeleton {
  padding: 24px;
}

/* 配送 */
.delivery-surface {
  margin-top: 20px;
  padding-bottom: 8px;
}

.delivery-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 0 20px 18px;
  align-items: center;
}

.delivery-field {
  flex: 1 1 260px;
  min-width: 200px;
}

.delivery-field :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
}

.delivery-mode {
  width: 140px;
  flex-shrink: 0;
}

.delivery-submit {
  flex-shrink: 0;
  font-weight: 600;
  background: linear-gradient(135deg, #ff6b35 0%, #ff8f65 100%) !important;
  border: none !important;
}

.delivery-result {
  padding: 0 20px 20px;
}

.delivery-stats {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.stat {
  background: #faf8f6;
  border-radius: var(--radius-md);
  padding: 10px 12px;
  border: 1px solid var(--color-border);
}

.stat-wide {
  grid-column: 1 / -1;
}

.stat-label {
  display: block;
  font-size: 0.72rem;
  color: var(--color-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 0.9rem;
  font-weight: 600;
}

.stat-accent {
  color: #e11d48;
}

.stat-wrap {
  word-break: break-all;
  font-weight: 500;
}

/* 页脚 */
.site-footer {
  text-align: center;
  padding: 20px 16px 28px;
  font-size: 0.75rem;
  color: #9ca3af;
}

/* Element 微调 */
.el-alert {
  border-radius: var(--radius-md);
}
</style>
