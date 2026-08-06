<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { toastInfo } from '../store/toast'
import { formatDuration } from '../utils'

const keyword = ref('')
const results = ref([])
const searching = ref(false)
const nickname = ref('')
const quota = ref(null)
const error = ref('')
const searchError = ref('')
const submitting = ref(false)

const modal = ref(null)   // 弹窗里选的歌
const flash = ref('')     // 成功提示

async function loadQuota() {
  try {
    quota.value = await api.getQuota()
  } catch {
    quota.value = null
  }
}

async function search() {
  const q = keyword.value.trim()
  if (!q) return
  searchError.value = ''
  searching.value = true
  try {
    results.value = await api.searchSongs(q, 10)
  } catch (e) {
    searchError.value = e.message
    results.value = []
  } finally {
    searching.value = false
  }
}

function openModal(song) {
  error.value = ''
  // 额度用尽：按钮可点但给提示
  if (quota.value && quota.value.remaining <= 0) {
    toastInfo(`你已点满 ${quota.value.limit} 首，等播完再点吧～`)
    return
  }
  modal.value = song
}

function closeModal() {
  if (submitting.value) return
  modal.value = null
}

async function submit() {
  if (!modal.value) return
  error.value = ''
  submitting.value = true
  try {
    const s = modal.value
    await api.requestSong({
      netease_id: s.id,
      song_name: s.name,
      artist: s.artist,
      album: s.album,
      album_id: s.album_id,
      cover: s.cover || '',
      duration: s.duration,
      nickname: nickname.value.trim() || null,
    })
    nickname.value = ''
    results.value = []
    keyword.value = ''
    await loadQuota()
    // 弹窗内直接显示成功状态
    modal.value = { done: true, name: s.name }
    flash.value = s.name
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

onMounted(loadQuota)
</script>

<template>
  <div class="request-page">
    <!-- 成功横幅 -->
    <div v-if="flash" class="flash-banner">
      ✅ 点歌成功「{{ flash }}」！已加入待播队列
      <button class="flash-close" @click="flash = ''">✕</button>
    </div>

    <section class="request-hero">
      <h1 class="page-title">🎤 我要点歌</h1>
      <p class="page-sub">搜索网易云音乐，点一首你喜欢的歌</p>

      <div v-if="quota" class="quota" :class="{ low: quota.remaining <= 1, admin: quota.remaining >= 999 }">
        {{
          quota.remaining >= 999
            ? '🎧 管理员模式：点歌不限'
            : quota.remaining > 0
              ? `你还能点 ${quota.remaining} 首（同一 IP 最多同时 ${quota.limit} 首）`
              : '你已点满 ' + quota.limit + ' 首，等广播站播完再点吧～'
        }}
      </div>

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="keyword"
          class="search-input"
          placeholder="输入歌名 / 歌手"
          @keyup.enter="search"
        />
        <button class="btn-primary" :disabled="searching" @click="search">
          {{ searching ? '搜索中…' : '搜索' }}
        </button>
      </div>
      <p v-if="searchError" class="error-text">{{ searchError }}</p>
    </section>

    <!-- 搜索结果 -->
    <section v-if="results.length" class="results">
      <div v-for="s in results" :key="s.id" class="result-item">
        <div class="cover" :class="{ placeholder: !s.cover }">
          <img v-if="s.cover" :src="s.cover" :alt="s.name" loading="lazy" />
          <span v-else class="cover-fallback">🎵</span>
        </div>
        <div class="result-info">
          <div class="result-name">{{ s.name }}</div>
          <div class="result-meta">{{ s.artist }}<span v-if="s.album"> · {{ s.album }}</span></div>
          <span class="result-duration">{{ formatDuration(s.duration) }}</span>
        </div>
        <button class="btn-pick" @click="openModal(s)">点这首</button>
      </div>
    </section>

    <!-- 点歌确认弹窗 -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="modal" class="modal-mask" @click.self="closeModal">
          <div class="modal-box">
            <!-- 成功状态 -->
            <template v-if="modal.done">
              <div class="modal-success">
                <div class="success-emoji">✅</div>
                <h3 class="modal-title">点歌成功！</h3>
                <p class="success-song">「{{ modal.name }}」已加入待播队列</p>
                <button class="btn-primary btn-block" @click="modal = null">好</button>
              </div>
            </template>
            <!-- 确认状态 -->
            <template v-else>
              <h3 class="modal-title">🎵 确认点歌</h3>
              <div class="modal-song">
                <div class="modal-cover" :class="{ placeholder: !modal.cover }">
                  <img v-if="modal.cover" :src="modal.cover" :alt="modal.name" />
                  <span v-else>🎵</span>
                </div>
                <div class="modal-info">
                  <div class="modal-name">{{ modal.name }}</div>
                  <div class="modal-meta">{{ modal.artist }} · {{ formatDuration(modal.duration) }}</div>
                </div>
              </div>
              <input
                v-model="nickname"
                class="input modal-nickname"
                maxlength="50"
                placeholder="你的昵称（可不填，匿名点歌）"
                @keyup.enter="submit"
              />
              <p v-if="error" class="error-text">{{ error }}</p>
              <div class="modal-actions">
                <button class="btn-ghost" :disabled="submitting" @click="closeModal">取消</button>
                <button class="btn-primary" :disabled="submitting" @click="submit">
                  {{ submitting ? '提交中…' : '确认点这首歌' }}
                </button>
              </div>
            </template>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>
