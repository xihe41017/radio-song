const BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, { method = 'GET', body, headers = {} } = {}) {
  const opts = { method, headers: { ...headers } }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(BASE + path, opts)
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(data.detail || '请求失败，请稍后再试')
    err.status = res.status
    throw err
  }
  return data
}

const authHeader = () => {
  const t = localStorage.getItem('radio_token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export const api = {
  // 听众
  searchSongs: (q, limit = 10) => request(`/songs/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  getQueue: () => request('/requests/queue'),
  getQuota: () => request('/requests/quota', { headers: authHeader() }),
  requestSong: (data) => request('/requests', { method: 'POST', body: data, headers: authHeader() }),

  // 管理
  adminLogin: (data) => request('/admin/login', { method: 'POST', body: data }),
  adminMe: () => request('/admin/me', { headers: authHeader() }),
  adminList: (status = '') => request(`/admin/requests${status ? '?status=' + status : ''}`, { headers: authHeader() }),
  adminMarkPlayed: (id) => request(`/admin/requests/${id}/played`, { method: 'POST', headers: authHeader() }),
  adminDelete: (id) => request(`/admin/requests/${id}`, { method: 'DELETE', headers: authHeader() }),
  adminChangePassword: (data) => request('/admin/password', { method: 'POST', body: data, headers: authHeader() }),

  // 系统设置
  adminSettings: () => request('/admin/settings', { headers: authHeader() }),
  adminUpdateSetting: (key, value) => request(`/admin/settings/${key}`, { method: 'PUT', body: { value }, headers: authHeader() }),

  // 自动更新（仅超管）
  autoUpdateStatus: () => request('/admin/auto-update', { headers: authHeader() }),
  autoUpdateSet: (enabled, interval) => request('/admin/auto-update', { method: 'PUT', body: { enabled, interval }, headers: authHeader() }),
  autoUpdateRun: () => request('/admin/auto-update/run', { method: 'POST', headers: authHeader() }),

  // Nginx 域名解析（仅超管）
  nginxStatus: () => request('/admin/nginx', { headers: authHeader() }),
  nginxInstall: () => request('/admin/nginx/install', { method: 'POST', headers: authHeader() }),
  nginxAddDomain: (data) => request('/admin/nginx/domains', { method: 'POST', body: data, headers: authHeader() }),
  nginxRemoveDomain: (domain) => request(`/admin/nginx/domains/${encodeURIComponent(domain)}`, { method: 'DELETE', headers: authHeader() }),

  // 账号管理（超管）
  adminUsers: () => request('/admin/users', { headers: authHeader() }),
  adminCreateUser: (data) => request('/admin/users', { method: 'POST', body: data, headers: authHeader() }),
  adminUpdateUser: (id, data) => request(`/admin/users/${id}`, { method: 'PUT', body: data, headers: authHeader() }),
  adminDeleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE', headers: authHeader() }),
}
