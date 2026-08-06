<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import ContentTab from '../components/admin/ContentTab.vue'
import SettingsTab from '../components/admin/SettingsTab.vue'
import UsersTab from '../components/admin/UsersTab.vue'

const token = ref(localStorage.getItem('radio_token') || '')
const me = ref(null)   // { username, role, permissions }
const loginForm = reactive({ username: '', password: '' })
const loginError = ref('')
const loggingIn = ref(false)

const tab = ref('content')

const isSuper = () => me.value?.role === 'super_admin'

const TABS = [
  { key: 'content', label: '🎵 点歌管理' },
  { key: 'settings', label: '⚙️ 系统设置' },
  { key: 'users', label: '👥 账号管理', super: true },
]
const visibleTabs = () => TABS.filter((t) => !t.super || isSuper())

async function doLogin() {
  loginError.value = ''
  loggingIn.value = true
  try {
    const r = await api.adminLogin(loginForm)
    token.value = r.token
    me.value = { username: r.username, role: r.role, permissions: r.permissions }
    localStorage.setItem('radio_token', r.token)
  } catch (e) {
    loginError.value = e.message
  } finally {
    loggingIn.value = false
  }
}

function logout() {
  token.value = ''
  me.value = null
  localStorage.removeItem('radio_token')
}

onMounted(async () => {
  if (token.value) {
    try {
      const r = await api.adminMe()
      me.value = { username: r.username, role: r.role, permissions: r.permissions }
    } catch {
      logout()
    }
  }
})
</script>

<template>
  <div class="admin-page">
    <!-- 登录 -->
    <div v-if="!token" class="login-card">
      <h1 class="login-title">📻 广播站管理</h1>
      <p class="login-sub">请输入管理员账号</p>
      <div class="form-field">
        <input v-model="loginForm.username" class="input" placeholder="用户名" @keyup.enter="doLogin" />
      </div>
      <div class="form-field">
        <input v-model="loginForm.password" class="input" type="password" placeholder="密码" @keyup.enter="doLogin" />
      </div>
      <p v-if="loginError" class="error-text">{{ loginError }}</p>
      <button class="btn-primary btn-block" :disabled="loggingIn" @click="doLogin">
        {{ loggingIn ? '登录中…' : '登录' }}
      </button>
    </div>

    <!-- 管理面板 -->
    <div v-else class="dashboard">
      <div class="dash-head">
        <div>
          <h1 class="page-title">📻 广播站管理</h1>
          <p class="dash-user">
            👋 {{ me?.username }}
            <span class="role-badge" :class="me?.role">{{ isSuper() ? '超级管理员' : '管理员' }}</span>
          </p>
        </div>
        <button class="btn-ghost btn-sm" @click="logout">退出</button>
      </div>

      <div class="tabs">
        <button v-for="t in visibleTabs()" :key="t.key" class="tab" :class="{ active: tab === t.key }" @click="tab = t.key">
          {{ t.label }}
        </button>
      </div>

      <ContentTab v-if="tab === 'content'" />
      <SettingsTab v-else-if="tab === 'settings'" :is-super="isSuper()" :perms="me?.permissions || []" />
      <UsersTab v-else-if="tab === 'users'" />
    </div>
  </div>
</template>
