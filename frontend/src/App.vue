<script setup>
import { useRoute } from 'vue-router'
import ToastHost from './components/ToastHost.vue'

const route = useRoute()
const links = [
  { to: '/', label: '🎧 点歌台' },
  { to: '/request', label: '🎤 我要点歌' },
]
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <nav class="nav">
        <router-link
          v-for="l in links"
          :key="l.to"
          :to="l.to"
          class="nav-link"
          :class="{ active: route.path === l.to }"
        >
          {{ l.label }}
        </router-link>
      </nav>
    </header>

    <main class="page">
      <router-view />
    </main>
    <ToastHost />
  </div>
</template>
