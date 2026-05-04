<template>
  <router-view />
</template>

<script setup>
import { onMounted, watch } from 'vue'

import { useUserStore } from '@/stores/user'
import { applyAdminTheme, resolveAdminTheme } from '@/utils/theme'

const userStore = useUserStore()

function syncAdminTheme() {
  applyAdminTheme(resolveAdminTheme(userStore.systemSettings || {}))
}

watch(() => userStore.systemSettings, syncAdminTheme, { deep: true })

onMounted(syncAdminTheme)
</script>
