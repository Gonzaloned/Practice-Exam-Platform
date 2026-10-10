<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppNavBar from '../components/AppNavBar.vue'
import { getCatalogExam } from '../data/catalog'
import { createAttemptForExam } from '../services/attemptCreate'
import { ExamSessionError } from '../services/attemptTypes'
import '../assets/styles/catalog.css'

const route = useRoute()
const router = useRouter()
const exam = computed(() => getCatalogExam(route.params.slug))
const confirmationStep = ref<0 | 1 | 2>(0)
const isStarting = ref(false)
const startError = ref('')

function openConfirmation() {
  confirmationStep.value = 1
  startError.value = ''
}

async function launchExam() {
  if (!exam.value || isStarting.value) {
    return
  }

  isStarting.value = true
  startError.value = ''
  try {
    const session = await createAttemptForExam(exam.value.slug)
    if (session.status === 'failed') {
      throw new Error('This exam session could not be started. Please try again.')
    }
    confirmationStep.value = 0
    await router.push({ name: 'exam-session', params: { sessionId: session.id } })
  } catch (error) {
    if (error instanceof ExamSessionError && error.status === 401) {
      await router.push({
        name: 'login',
        query: { redirect: route.fullPath },
      })
      return
    }
    startError.value = error instanceof Error
      ? error.message
      : 'Unable to start the exam. Please try again.'
  } finally {
    isStarting.value = false
  }
}
</script>

<template>
  <div class="public-page">
    <AppNavBar active-link="exams" />

    <main v-if="exam" class="exam-details-page">
      <RouterLink to="/exams" class="catalog-back-link">
        <span aria-hidden="true">←</span>
        Back to exam catalog
      </RouterLink>

      <section class="exam-details-hero">
        <div class="exam-details-heading">
          <div class="catalog-exam-icon">{{ exam.icon }}</div>
          <div>
            <div class="catalog-eyebrow">{{ exam.provider }}</div>
            <span class="catalog-status">
              <span class="catalog-status-dot"></span>
              Available to start
            </span>
          </div>
        </div>

        <h1>{{ exam.title }}</h1>
        <p>{{ exam.description }}</p>

        <div class="exam-details-meta">
          <div>
            <span class="exam-meta-label">FORMAT</span>
            <strong>{{ exam.format }}</strong>
          </div>
          <div>
            <span class="exam-meta-label">TASKS</span>
            <strong>{{ exam.taskCount }} practical tasks</strong>
          </div>
        </div>

        <button type="button" class="primary-link exam-start-link" @click="openConfirmation">
          Start exam
          <span aria-hidden="true">→</span>
        </button>
      </section>

      <section class="exam-details-section">
        <div class="catalog-eyebrow">WHAT YOU'LL PRACTICE</div>
        <h2>Skills covered</h2>
        <p>
          Complete realistic administration tasks across the core areas below.
          You can move between tasks in the exam workspace.
        </p>

        <ul class="exam-topic-list">
          <li v-for="topic in exam.topics" :key="topic">
            <span class="exam-topic-check" aria-hidden="true">✓</span>
            {{ topic }}
          </li>
        </ul>
      </section>

      <section class="exam-ready-panel">
        <div>
          <h2>Ready to begin?</h2>
          <p>Your practice session will open in the exam workspace.</p>
        </div>
        <button type="button" class="primary-link" @click="openConfirmation">
          Start exam
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </main>

    <main v-else class="exam-details-page exam-not-found">
      <div class="catalog-eyebrow">EXAM NOT FOUND</div>
      <h1>This exam isn't in the catalog.</h1>
      <p>Choose an available practice exam from the catalog.</p>
      <RouterLink to="/exams" class="primary-link">Browse exams</RouterLink>
    </main>

    <Teleport to="body">
      <div
        v-if="confirmationStep"
        class="exam-confirmation-backdrop"
        @click.self="confirmationStep = 0"
      >
        <section
          class="exam-confirmation-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="exam-confirmation-title"
          aria-describedby="exam-confirmation-description"
        >
          <button
            type="button"
            class="exam-confirmation-close"
            aria-label="Close confirmation"
            :disabled="isStarting"
            @click="confirmationStep = 0"
          >
            ×
          </button>

          <template v-if="confirmationStep === 1">
            <div class="catalog-eyebrow">BEFORE YOU BEGIN</div>
            <h2 id="exam-confirmation-title">Start a dedicated exam session?</h2>
            <p id="exam-confirmation-description">
              ExamLab will prepare an isolated Linux environment for your account.
              Your session is authorized for up to 24 hours and the environment
              will be stopped when you finish or the session expires.
            </p>
            <div class="exam-confirmation-notice">
              <strong>Make sure you're ready.</strong>
              <span>Starting may take a few minutes while your environment is prepared.</span>
            </div>
            <div class="exam-confirmation-actions">
              <button type="button" class="confirmation-secondary" @click="confirmationStep = 0">
                Cancel
              </button>
              <button type="button" class="primary-link" @click="confirmationStep = 2">
                Continue
                <span aria-hidden="true">→</span>
              </button>
            </div>
          </template>

          <template v-else>
            <div class="catalog-eyebrow">FINAL CONFIRMATION</div>
            <h2 id="exam-confirmation-title">Provision your exam environment?</h2>
            <p id="exam-confirmation-description">
              Confirm to create or resume your personal {{ exam?.provider }} practice session.
            </p>
            <div v-if="startError" class="exam-start-error" role="alert">
              {{ startError }}
            </div>
            <div class="exam-confirmation-actions">
              <button
                type="button"
                class="confirmation-secondary"
                :disabled="isStarting"
                @click="confirmationStep = 1"
              >
                Go back
              </button>
              <button
                type="button"
                class="primary-link"
                :disabled="isStarting"
                @click="launchExam"
              >
                {{ isStarting ? 'Preparing...' : 'Confirm and start' }}
                <span v-if="!isStarting" aria-hidden="true">→</span>
              </button>
            </div>
          </template>
        </section>
      </div>
    </Teleport>
  </div>
</template>
