<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { toastSuccess, toastError } from '../../store/toast'

const props = defineProps({
  isSuper: { type: Boolean, default: false },
  perms: { type: Array, default: () => [] },
})

const settings = ref([])
const loading = ref(false)
const saving = ref({})
const pwd = reactive({ old_password: '', new_password: '' })
const pwdMsg = ref('')

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

onMounted(load)
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

    <h3 class="sub-title">🔑 修改我的密码</h3>
    <div class="pwd-card">
      <input v-model="pwd.old_password" class="input" type="password" placeholder="原密码" />
      <input v-model="pwd.new_password" class="input" type="password" placeholder="新密码（≥6位）" />
      <button class="btn-primary btn-sm" @click="savePassword">确认修改</button>
      <p v-if="pwdMsg" class="pwd-msg">{{ pwdMsg }}</p>
    </div>
  </div>
</template>
