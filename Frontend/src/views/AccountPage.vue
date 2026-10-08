<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppNavBar from '../components/AppNavBar.vue'
import '../assets/styles/account.css'

const route = useRoute()

const title = computed(() =>
  typeof route.meta.title === 'string' ? route.meta.title : 'Account'
)
const description = computed(() =>
  typeof route.meta.description === 'string' ? route.meta.description : ''
)
const emptyMessage = computed(() =>
  typeof route.meta.emptyMessage === 'string' ? route.meta.emptyMessage : ''
)
</script>

<template>
  <div class="account-page">
    <AppNavBar />

    <main class="account-content">
      <div class="account-eyebrow">YOUR ACCOUNT</div>
      <h1>{{ title }}</h1>
      <p class="account-description">{{ description }}</p>

      <section class="account-empty-state">
        <h2>{{ emptyMessage }}</h2>
        <p>This area is ready for your ExamLab account information.</p>
        <RouterLink to="/exams">Browse exams</RouterLink>
      </section>
    </main>
  </div>
</template>
