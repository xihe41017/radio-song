<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../../api'
import { toastSuccess, toastError } from '../../store/toast'
import { formatDuration, formatFull } from '../../utils'

const filter = ref('pending')
const items = ref([])
const stats = ref(null)
const loading = ref(false)
const busy = ref({})

const TABS = [
  { key: 'pending', label: '⏳ 待播放' },
  { key: 'played', label: '✅ 已播放' },
  { key: 'all', label: '📋 全部' },
]

async function load() {
  loading.value = true
  try {
    const d = await api.adminList(filter.value === 'all' ? '' : filter.value)
    items.value = d.items
    stats.value = d.stats
  } finally {
    loading.value = false
  }
}

function switchTab(k) {
  filter.value = k
  load()
}

async function markPlayed(r) {
  busy.value[r.id] = true
  try {
    await api.adminMarkPlayed(r.id)
    toastSuccess(`「${r.song_name}」已标记播放`)
    if (filter.value === 'pending') items.value = items.value.filter((x) => x.id !== r.id)
    else await load()
  } catch (e) {
    toastError(e.message)
  } finally {
    busy.value[r.id] = false
  }
}

async function del(r) {
  if (!confirm(`确定删除「${r.song_name}」这条点歌吗？`)) return
  busy.value[r.id] = true
  try {
    await api.adminDelete(r.id)
    toastSuccess('已删除')
    items.value = items.value.filter((x) => x.id !== r.id)
  } catch (e) {
    toastError(e.message)
  } finally {
    busy.value[r.id] = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div v-if="stats" class="stats">
      <div class="stat-card"><span class="stat-num">{{ stats.pending }}</span><span class="stat-label">待播放</span></div>
      <div class="stat-card"><span class="stat-num">{{ stats.played }}</span><span class="stat-label">已播放</span></div>
      <div class="stat-card"><span class="stat-num">{{ stats.total }}</span><span class="stat-label">累计</span></div>
    </div>

    <div class="tabs">
      <button v-for="t in TABS" :key="t.key" class="tab" :class="{ active: filter === t.key }" @click="switchTab(t.key)">
        {{ t.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="items.length" class="admin-list">
      <div v-for="r in items" :key="r.id" class="admin-item">
        <div class="cover" :class="{ placeholder: !r.cover }">
          <img v-if="r.cover" :src="r.cover" :alt="r.song_name" loading="lazy" />
          <span v-else>🎵</span>
        </div>
        <div class="admin-info">
          <div class="admin-song">{{ r.song_name }}</div>
          <div class="admin-artist">{{ r.artist }}</div>
          <div class="admin-meta">
            <span>🙋 {{ r.nickname || '匿名听众' }}</span>
            <span>· IP {{ r.ip }}</span>
            <span>· {{ formatFull(r.created_at) }}</span>
            <span v-if="r.duration">· {{ formatDuration(r.duration) }}</span>
            <span v-if="r.status === 'played'" class="badge-played">✅ 已播 {{ formatFull(r.played_at) }}</span>
          </div>
        </div>
        <div class="admin-actions">
          <button v-if="r.status === 'pending'" class="btn-play" :disabled="busy[r.id]" @click="markPlayed(r)">▶ 已播放</button>
          <button class="btn-del" :disabled="busy[r.id]" @click="del(r)">🗑</button>
        </div>
      </div>
    </div>
    <div v-else class="empty">
      <div class="empty-emoji">📭</div>
      <p>这里没有{{ filter === 'pending' ? '待播放' : filter === 'played' ? '已播放' : '' }}的点歌</p>
    </div>
  </div>
</template>
