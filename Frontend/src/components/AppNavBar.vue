<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearAccessToken, hasAccessToken } from '../services/auth'
import '../assets/styles/navbar.css'

withDefaults(defineProps<{
  activeLink?: 'exams' | 'about'
}>(), {
  activeLink: undefined,
})

const route = useRoute()
const router = useRouter()
const isAuthenticated = ref(hasAccessToken())
const isMenuOpen = ref(false)
const menuRoot = ref<HTMLElement | null>(null)

function syncAuthentication() {
  isAuthenticated.value = hasAccessToken()
}

function closeMenuOnOutsideClick(event: PointerEvent) {
  if (event.target instanceof Node && !menuRoot.value?.contains(event.target)) {
    isMenuOpen.value = false
  }
}

function closeMenuOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    isMenuOpen.value = false
  }
}

function logout() {
  clearAccessToken()
  isAuthenticated.value = false
  isMenuOpen.value = false
  void router.push('/')
}

watch(() => route.fullPath, () => {
  isMenuOpen.value = false
  syncAuthentication()
})

onMounted(() => {
  syncAuthentication()
  document.addEventListener('pointerdown', closeMenuOnOutsideClick)
  document.addEventListener('keydown', closeMenuOnEscape)
  window.addEventListener('storage', syncAuthentication)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', closeMenuOnOutsideClick)
  document.removeEventListener('keydown', closeMenuOnEscape)
  window.removeEventListener('storage', syncAuthentication)
})
</script>

<template>
  <header class="app-navbar">
    <RouterLink to="/" class="app-navbar-brand">
      <span class="app-navbar-brand-mark">E</span>
      <span class="app-navbar-brand-copy">
        <span class="app-navbar-brand-name">ExamLab</span>
        <span class="app-navbar-brand-subtitle">Certification Practice</span>
      </span>
    </RouterLink>

    <nav class="app-navbar-links" aria-label="Main navigation">
      <RouterLink
        to="/exams"
        :class="{ 'is-active': activeLink === 'exams' }"
      >
        Exams
      </RouterLink>
      <RouterLink
        to="/about"
        :class="{ 'is-active': activeLink === 'about' }"
      >
        About
      </RouterLink>
      <RouterLink v-if="isAuthenticated" to="/examtry">
        ExamTry
      </RouterLink>

      <RouterLink
        v-if="!isAuthenticated"
        to="/login"
        class="app-navbar-sign-in"
      >
        Sign in
      </RouterLink>

      <div
        v-else
        ref="menuRoot"
        class="app-navbar-account"
      >
        <button
          type="button"
          class="app-navbar-account-trigger"
          aria-haspopup="true"
          aria-controls="account-menu"
          :aria-expanded="isMenuOpen"
          @click="isMenuOpen = !isMenuOpen"
        >
          <span class="app-navbar-avatar" aria-hidden="true">A</span>
          <span>Account</span>
          <span class="app-navbar-chevron" aria-hidden="true">⌄</span>
        </button>

        <div
          v-if="isMenuOpen"
          id="account-menu"
          class="app-navbar-menu"
          aria-label="Account menu"
        >
          <RouterLink to="/profile">My profile</RouterLink>
          <RouterLink to="/my-exams">My exams</RouterLink>
          <RouterLink to="/settings">Settings</RouterLink>
          <button
            type="button"
            class="app-navbar-logout"
            @click="logout"
          >
            Log out
          </button>
        </div>
      </div>
    </nav>
  </header>
</template>
