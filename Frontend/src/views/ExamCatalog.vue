<script setup lang="ts">
import AppNavBar from '../components/AppNavBar.vue'
import { catalogExams } from '../data/catalog'
import '../assets/styles/catalog.css'
</script>

<template>
  <div class="public-page">
    <AppNavBar active-link="exams" />

    <main class="catalog-page">
      <section class="catalog-intro">
        <div class="catalog-eyebrow">EXAM CATALOG</div>
        <h1>Choose your next certification.</h1>
        <p>
          Explore hands-on practice exams and find the right challenge
          for your certification goals.
        </p>
      </section>

      <section class="catalog-list" aria-labelledby="catalog-heading">
        <div class="catalog-heading">
          <div>
            <div class="catalog-eyebrow">AVAILABLE NOW</div>
            <h2 id="catalog-heading">Practice exams</h2>
          </div>
          <span class="catalog-count">
            {{ catalogExams.length }} {{ catalogExams.length === 1 ? 'exam' : 'exams' }}
          </span>
        </div>

        <div class="catalog-grid">
          <article
            v-for="exam in catalogExams"
            :key="exam.slug"
            class="catalog-card"
          >
            <div class="catalog-card-top">
              <div class="catalog-exam-icon">{{ exam.icon }}</div>
              <span class="catalog-status">
                <span class="catalog-status-dot"></span>
                Available
              </span>
            </div>

            <div class="catalog-provider">{{ exam.provider }}</div>
            <h3>{{ exam.title }}</h3>
            <p>{{ exam.summary }}</p>

            <div class="catalog-card-meta">
              <span>{{ exam.taskCount }} hands-on tasks</span>
              <span>{{ exam.topics.length }} topic areas</span>
            </div>

            <RouterLink
              :to="{ name: 'exam-details', params: { slug: exam.slug } }"
              class="catalog-card-link"
            >
              View exam details
              <span aria-hidden="true">→</span>
            </RouterLink>
          </article>
        </div>
      </section>
    </main>

    <footer class="main-footer">
      ExamLab · Certification Practice Platform · 2026
    </footer>
  </div>
</template>
