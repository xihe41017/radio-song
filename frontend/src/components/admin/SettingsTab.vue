<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { toastSuccess, toastError, toastInfo } from '../../store/toast'

const props = defineProps({
  isSuper: { type: Boolean, default: false },
  perms: { type: Array, default: () => [] },
})

const settings = ref([])
const loading = ref(false)
const saving = ref({})
const pwd = reactive({ old_password: '', new_password: '' })
const pwdMsg = ref('')

// 自动更新（仅超管）
const au = ref(null)
const auSaving = ref(false)
const auRunning = ref(false)

async function loadAutoUpdate() {
  if (!props.isSuper) return
  try {
    au.value = await api.autoUpdateStatus()
  } catch (e) {
    toastError(e.message)
  }
}

async function saveAutoUpdate() {
  if (!au.value) return
  auSaving.value = true
  try {
    au.value = await api.autoUpdateSet(au.value.enabled, Number(au.value.interval))
    toastSuccess('自动更新设置已保存')
  } catch (e) {
    toastError(e.message)
  } finally {
    auSaving.value = false
  }
}

async function runAutoUpdate() {
  if (!au.value) return
  if (au.value.updating) return toastInfo('正在更新中，请稍候')
  auRunning.value = true
  try {
    au.value = await api.autoUpdateRun()
    toastInfo(au.value.last_result)
    setTimeout(loadAutoUpdate, 3000)
  } catch (e) {
    toastError(e.message)
  } finally {
    auRunning.value = false
  }
}

const LABELS = {
  site_name: '站点名称',
  request_limit: '单IP点歌数',
  rate_search: '搜索限速',
  rate_request: '点歌限速',
  rate_login: '登录限速',
  jwt_secret: 'JWT 密钥',
}

// 该设置当前管理员能否编辑
function canEdit(s) {
  if (s.sensitive) return props.isSuper
  return props.perms.includes(`settings.${s.key}`)
}

// 仅显示有权限的设置项
const visibleSettings = computed(() =>
  props.isSuper ? settings.value : settings.value.filter(canEdit)
)

async function load() {
  loading.value = true
  try {
    settings.value = await api.adminSettings()
  } finally {
    loading.value = false
  }
}

async function save(s) {
  saving.value[s.key] = true
  try {
    await api.adminUpdateSetting(s.key, String(s.value))
    toastSuccess('已保存')
  } catch (e) {
    toastError(e.message)
  } finally {
    saving.value[s.key] = false
  }
}

async function savePassword() {
  pwdMsg.value = ''
  if (pwd.new_password.length < 6) return (pwdMsg.value = '新密码至少 6 位')
  try {
    await api.adminChangePassword(pwd)
    pwdMsg.value = '✅ 密码修改成功'
    pwd.old_password = ''
    pwd.new_password = ''
  } catch (e) {
    pwdMsg.value = e.message
  }
}

onMounted(() => {
  load()
  loadAutoUpdate()
})
</script>

<template>
  <div>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!visibleSettings.length" class="empty">
      <div class="empty-emoji">🔒</div>
      <p>没有你可管理的设置项</p>
    </div>
    <div v-else class="settings-list">
      <div v-for="s in visibleSettings" :key="s.key" class="setting-item">
        <div class="setting-name-row">
          <span class="setting-name">{{ LABELS[s.key] || s.key }}</span>
          <code class="setting-key">{{ s.key }}</code>
          <span v-if="s.sensitive" class="sensitive-badge">🔒 仅超管</span>
        </div>
        <p class="setting-desc">{{ s.description }}</p>
        <div class="setting-control">
          <input
            v-model="s.value"
            class="input setting-input"
            type="text"
            inputmode="numeric"
            :placeholder="s.key.startsWith('rate_') ? '输入数字，如 20' : ''"
          />
          <button class="btn-play" :disabled="saving[s.key]" @click="save(s)">
            {{ saving[s.key] ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 自动更新（仅超管） -->
    <template v-if="props.isSuper">
      <h3 class="sub-title">🔄 自动更新</h3>
      <div v-if="au" class="auto-update-card">
        <div class="setting-item">
          <div class="setting-name-row">
            <span class="setting-name">自动更新</span>
            <span v-if="au.script_exists" class="sensitive-badge">服务器环境可用</span>
            <span v-else class="lock-badge">仅服务器部署环境可用</span>
            <span v-if="au.updating" class="au-updating">⏳ 更新中…</span>
          </div>
          <p class="setting-desc">检查 GitHub 是否有新代码，有则自动拉取构建并重启；任何一步失败都保持当前版本。</p>
          <div class="setting-control au-control">
            <label class="anon-switch">
              <input v-model="au.enabled" type="checkbox" />
              <span class="anon-switch-slider"></span>
              <span class="anon-switch-label">启用自动更新</span>
            </label>
            <div class="au-interval">
              <input v-model="au.interval" class="input setting-input" type="number" min="1" max="1440" />
              <span class="au-unit">分钟检查一次</span>
            </div>
            <button class="btn-primary btn-sm" :disabled="auSaving" @click="saveAutoUpdate">保存规则</button>
          </div>
          <div class="au-status">
            <span>最近结果：{{ au.last_result || '尚未执行' }}</span>
            <button class="btn-play" :disabled="auRunning || au.updating" @click="runAutoUpdate">
              {{ auRunning ? '启动中…' : '⚡ 立即更新' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <h3 class="sub-title">🔑 修改我的密码</h3>
    <div class="pwd-card">
      <input v-model="pwd.old_password" class="input" type="password" placeholder="原密码" />
      <input v-model="pwd.new_password" class="input" type="password" placeholder="新密码（≥6位）" />
      <button class="btn-primary btn-sm" @click="savePassword">确认修改</button>
      <p v-if="pwdMsg" class="pwd-msg">{{ pwdMsg }}</p>
    </div>
  </div>
</template>
