<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { toastSuccess, toastError } from '../../store/toast'
import { formatFull } from '../../utils'

const PERMS = [
  { key: 'content.manage', label: '点歌管理（标记已播/删除）' },
  { key: 'settings.view', label: '查看系统设置' },
  { key: 'settings.site_name', label: '修改：站点名称' },
  { key: 'settings.request_limit', label: '修改：单IP点歌数' },
]

const users = ref([])
const loading = ref(false)
const error = ref('')
const createForm = reactive({ username: '', password: '', role: 'admin' })
const permModal = ref(null) // { user, perms: Set }

async function load() {
  loading.value = true
  try {
    users.value = await api.adminUsers()
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function createUser() {
  error.value = ''
  if (createForm.username.length < 3) return (error.value = '用户名至少 3 位')
  if (createForm.password.length < 6) return (error.value = '密码至少 6 位')
  try {
    await api.adminCreateUser({ ...createForm, permissions: [] })
    createForm.username = ''
    createForm.password = ''
    await load()
    toastSuccess('用户创建成功')
  } catch (e) {
    error.value = e.message
  }
}

function openPerms(u) {
  permModal.value = { user: u, perms: new Set(u.permissions || []) }
}
function togglePerm(key) {
  const set = permModal.value.perms
  if (set.has(key)) set.delete(key)
  else set.add(key)
}
async function savePerms() {
  const m = permModal.value
  try {
    await api.adminUpdateUser(m.user.id, { permissions: [...m.perms] })
    permModal.value = null
    await load()
    toastSuccess('权限已保存')
  } catch (e) {
    toastError(e.message)
  }
}
async function setRole(u, role) {
  try {
    await api.adminUpdateUser(u.id, { role })
    toastSuccess('角色已修改')
    await load()
  } catch (e) {
    toastError(e.message)
  }
}
async function resetPwd(u) {
  const pw = prompt(`为 ${u.username} 设置新密码（≥6位）：`)
  if (!pw || pw.length < 6) return toastError('密码至少 6 位')
  try {
    await api.adminUpdateUser(u.id, { password: pw })
    toastSuccess('密码已重置')
  } catch (e) {
    toastError(e.message)
  }
}
async function delUser(u) {
  if (!confirm(`确定删除管理员 ${u.username} 吗？`)) return
  try {
    await api.adminDeleteUser(u.id)
    toastSuccess('已删除')
    await load()
  } catch (e) {
    toastError(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <!-- 新建用户 -->
    <div class="create-user">
      <h3 class="sub-title">➕ 新建管理员</h3>
      <div class="create-row">
        <input v-model="createForm.username" class="input" placeholder="用户名" />
        <input v-model="createForm.password" class="input" type="password" placeholder="密码（≥6位）" />
        <select v-model="createForm.role" class="input select">
          <option value="admin">普通管理员</option>
          <option value="super_admin">超级管理员</option>
        </select>
        <button class="btn-primary btn-sm" @click="createUser">创建</button>
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
    </div>

    <!-- 用户列表 -->
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="users.length" class="admin-list">
      <div v-for="u in users" :key="u.id" class="user-item">
        <div class="user-main">
          <div class="user-name-row">
            <span class="user-name">{{ u.username }}</span>
            <span class="role-badge" :class="u.role">{{ u.role === 'super_admin' ? '超级管理员' : '管理员' }}</span>
            <span class="user-time">{{ formatFull(u.created_at) }}</span>
          </div>
          <div class="user-perms">
            <template v-if="u.role !== 'super_admin'">
              <span v-for="p in u.permissions" :key="p" class="perm-chip">{{ p.split('.').pop() }}</span>
              <span v-if="!u.permissions.length" class="perm-chip none">无</span>
            </template>
            <span v-else class="perm-chip super">全部权限</span>
          </div>
        </div>
        <div class="user-actions">
          <select class="input select" :value="u.role" @change="(e) => setRole(u, e.target.value)">
            <option value="admin">管理员</option>
            <option value="super_admin">超管</option>
          </select>
          <button class="btn-ghost btn-sm" @click="openPerms(u)">🔐 权限</button>
          <button class="btn-ghost btn-sm" @click="resetPwd(u)">🔑 改密</button>
          <button class="btn-del" @click="delUser(u)">🗑</button>
        </div>
      </div>
    </div>

    <!-- 权限弹窗 -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="permModal" class="modal-mask" @click.self="permModal = null">
          <div class="modal-box">
            <h3 class="modal-title">🔐 {{ permModal.user.username }} 的权限</h3>
            <p class="modal-sub">超管可单独授予/收回每个管理员的权限</p>
            <div v-for="p in PERMS" :key="p.key" class="perm-item">
              <label class="perm-label">
                <input type="checkbox" :checked="permModal.perms.has(p.key)" @change="togglePerm(p.key)" />
                <span>{{ p.label }}</span>
              </label>
            </div>
            <div class="modal-actions">
              <button class="btn-ghost" @click="permModal = null">取消</button>
              <button class="btn-primary" @click="savePerms">保存</button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>
