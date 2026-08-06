<script setup>
import { toasts } from '../store/toast'
</script>

<template>
  <div class="toast-host">
    <transition-group name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">{{ t.message }}</div>
    </transition-group>
  </div>
</template>
