<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { toastSuccess, toastError } from '../../store/toast'

const st = ref(null)
const loading = ref(false)
const busy = ref(false)
const form = reactive({ domain: '', ssl_cert: '', ssl_key: '' })
const showPreview = ref(false)

async function load() {
  loading.value = true
  try {
    st.value = await api.nginxStatus()
  } catch (e) {
    toastError(e.message)
  } finally {
    loading.value = false
  }
}

async function installNginx() {
  busy.value = true
  try {
    st.value = await api.nginxInstall()
    toastSuccess('Nginx 安装完成')
  } catch (e) {
    toastError(e.message)
  } finally {
    busy.value = false
  }
}

async function addDomain() {
  if (!form.domain.trim()) return toastError('请输入域名')
  busy.value = true
  try {
    st.value = await api.nginxAddDomain({ ...form })
    toastSuccess(`已绑定域名 ${form.domain.trim()}`)
    form.domain = ''
    form.ssl_cert = ''
    form.ssl_key = ''
  } catch (e) {
    toastError(e.message)
  } finally {
    busy.value = false
  }
}

async function removeDomain(domain) {
  if (!confirm(`确认解除域名 ${domain} 的绑定？`)) return
  busy.value = true
  try {
    st.value = await api.nginxRemoveDomain(domain)
    toastSuccess(`已解除 ${domain}`)
  } catch (e) {
    toastError(e.message)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!st" class="empty">
      <div class="empty-emoji">🌐</div>
      <p class="empty-text">域名解析功能不可用</p>
    </div>
    <template v-else>
      <!-- 环境状态 -->
      <h3 class="sub-title">🌐 域名解析（Nginx）</h3>
      <div class="setting-item">
        <div class="setting-name-row">
          <span class="setting-name">运行环境</span>
          <span v-if="st.is_server" class="sensitive-badge">Linux 服务器</span>
          <span v-else class="lock-badge">Windows 开发环境（仅预览）</span>
        </div>
        <div class="nginx-status">
          <span>Nginx：{{ st.nginx_installed ? (st.nginx_active ? '✅ 已安装运行' : '⚠️ 已安装未运行') : '❌ 未安装' }}</span>
          <span>后端端口：{{ st.port }}</span>
          <span v-if="st.is_server" class="nginx-file">配置：{{ st.conf_file }}</span>
        </div>
        <div class="setting-control au-control">
          <button v-if="!st.nginx_installed && st.is_server" class="btn-primary btn-sm" :disabled="busy" @click="installNginx">
            {{ busy ? '安装中…' : '📥 安装 Nginx' }}
          </button>
          <span v-if="!st.is_server" class="setting-desc">开发环境不写 Nginx，仅预览生成配置</span>
        </div>
      </div>

      <!-- 添加域名 -->
      <div class="setting-item">
        <div class="setting-name-row">
          <span class="setting-name">绑定域名</span>
          <code class="setting-key">server_name</code>
        </div>
        <p class="setting-desc">将该域名反向代理到本系统端口 {{ st.port }}。格式如 radio.example.com</p>
        <div class="nginx-form">
          <input v-model="form.domain" class="input" placeholder="域名，如 radio.example.com" :disabled="!st.is_server || busy" />
          <input v-model="form.ssl_cert" class="input" placeholder="HTTPS 证书路径（可选）" :disabled="!st.is_server || busy" />
          <input v-model="form.ssl_key" class="input" placeholder="HTTPS 私钥路径（可选）" :disabled="!st.is_server || busy" />
          <button class="btn-play" :disabled="!st.is_server || busy" @click="addDomain">
            {{ busy ? '处理中…' : '绑定' }}
          </button>
        </div>
        <p class="setting-desc">同时填证书和私钥则启用 HTTPS；留空为纯 HTTP。</p>
      </div>

      <!-- 已绑定域名列表 -->
      <div class="setting-item">
        <div class="setting-name-row">
          <span class="setting-name">已绑定域名（{{ st.domains.length }}）</span>
          <button class="btn-ghost btn-sm" @click="showPreview = !showPreview">
            {{ showPreview ? '隐藏配置' : '预览 Nginx 配置' }}
          </button>
        </div>
        <div v-if="!st.domains.length" class="empty">
          <div class="empty-emoji">🔗</div>
          <p class="empty-text">尚未绑定任何域名</p>
        </div>
        <div v-else class="domain-list">
          <div v-for="d in st.domains" :key="d.domain" class="domain-row">
            <span class="domain-name">{{ d.domain }}</span>
            <span v-if="d.ssl_cert" class="sensitive-badge">🔒 HTTPS</span>
            <button class="btn-ghost btn-sm domain-del" :disabled="busy" @click="removeDomain(d.domain)">删除</button>
          </div>
        </div>
        <pre v-if="showPreview" class="nginx-preview">{{ st.preview }}</pre>
      </div>
    </template>
  </div>
</template>

<style scoped>
.nginx-status {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin: 6px 0 10px;
}
.nginx-file {
  font-family: monospace;
}
.nginx-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}
.nginx-form .input {
  width: 100%;
}
.domain-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.domain-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}
.domain-name {
  font-family: monospace;
  flex: 1;
  word-break: break-all;
}
.domain-del {
  flex-shrink: 0;
}
.nginx-preview {
  margin-top: 10px;
  padding: 12px;
  background: #0f172a;
  color: #cbd5e1;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 320px;
  overflow-y: auto;
}
</style>
