<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { formatDuration, formatTime } from '../utils'

const router = useRouter()
const queue = ref({ pending: [], played: [] })
const loading = ref(true)
const error = ref('')

async function load() {
  try {
    queue.value = await api.getQueue()
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(load)

const fmt = (sec) => formatDuration(sec)
const cover = (r) => r.cover || ''
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="disc" aria-hidden="true">
        <span class="disc-ring"></span>
        <span class="disc-center">🎵</span>
      </div>
      <div class="hero-text">
        <div class="equalizer" aria-hidden="true">
          <span v-for="i in 5" :key="i" class="eq-bar" :style="{ animationDelay: i * 0.12 + 's' }"></span>
        </div>
        <h1 class="hero-title">广播站点歌台</h1>
        <p class="hero-sub">把你想听的歌，点给广播站 🎧</p>
        <button class="btn-primary" @click="router.push('/request')">🎤 我要点歌</button>
      </div>
    </section>

    <!-- 待播队列 -->
    <section class="section">
      <div class="section-head">
        <h2 class="section-title"><span class="live-dot"></span> 待播放</h2>
        <span class="section-count">{{ queue.pending.length }} 首排队中</span>
      </div>

      <div v-if="loading" class="loading">加载中…</div>
      <p v-else-if="error" class="error-text">{{ error }}</p>

      <div v-else-if="queue.pending.length" class="queue-list">
        <div v-for="(r, i) in queue.pending" :key="r.id" class="queue-item" :class="{ playing: i === 0 }">
          <span class="queue-pos">{{ i + 1 }}</span>
          <div class="cover" :class="{ placeholder: !cover(r) }">
            <img v-if="cover(r)" :src="r.cover" :alt="r.song_name" loading="lazy" />
            <span v-else class="cover-fallback">🎵</span>
          </div>
          <div class="queue-info">
            <div class="queue-song">{{ r.song_name }}</div>
            <div class="queue-artist">{{ r.artist }} <span v-if="r.album">· {{ r.album }}</span></div>
            <div class="queue-meta">
              <span>🙋 {{ r.nickname || '匿名听众' }}</span>
              <span>· {{ formatTime(r.created_at) }}</span>
              <span v-if="r.duration" class="duration">· {{ fmt(r.duration) }}</span>
            </div>
          </div>
          <span v-if="i === 0" class="now-badge">▶ 下一首</span>
        </div>
      </div>

      <div v-else class="empty">
        <div class="empty-emoji">📻</div>
        <p>待播列表空空的，快来点一首吧</p>
        <button class="btn-primary" @click="router.push('/request')">去点歌 →</button>
      </div>
    </section>

    <!-- 已播历史 -->
    <section class="section" v-if="queue.played.length">
      <div class="section-head">
        <h2 class="section-title">🎶 已播放</h2>
        <span class="section-count">最近 {{ queue.played.length }} 首</span>
      </div>
      <div class="played-list">
        <div v-for="(r, i) in queue.played" :key="r.id" class="played-item">
          <div class="cover sm" :class="{ placeholder: !cover(r) }">
            <img v-if="cover(r)" :src="r.cover" :alt="r.song_name" loading="lazy" />
            <span v-else class="cover-fallback">🎵</span>
          </div>
          <div class="played-info">
            <span class="played-song">{{ r.song_name }}</span>
            <span class="played-artist">{{ r.artist }}</span>
          </div>
          <span class="played-time">{{ formatTime(r.played_at) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
