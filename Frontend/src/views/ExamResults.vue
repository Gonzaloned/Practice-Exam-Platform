<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ExamSessionError, expireLocalLogin, getExamSession, type ExamSession } from '../services/examSessions'

const route = useRoute()
const router = useRouter()
const session = ref<ExamSession | null>(null)
const errorMessage = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const result = await getExamSession(String(route.params.sessionId))
    if (result.status === 'running' || result.status === 'provisioning') {
      await router.replace({
        name: 'exam-session',
        params: { sessionId: result.id },
      })
      return
    }
    session.value = result
    if (result.cleanup_error) {
      errorMessage.value = `The environment could not be shut down automatically: ${result.cleanup_error}`
    }
  } catch (error) {
    if (error instanceof ExamSessionError && error.status === 401) {
      expireLocalLogin()
      await router.replace({
        name: 'login',
        query: { redirect: route.fullPath },
      })
      return
    }
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to load this exam result.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="exam-lifecycle-page">
    <section class="exam-lifecycle-card" aria-live="polite">
      <div v-if="loading" class="exam-loader" aria-hidden="true"></div>
      <template v-else-if="session">
        <div class="catalog-eyebrow">
          {{ session.status === 'expired'
            ? 'SESSION EXPIRED'
            : session.status === 'completed'
              ? 'SESSION COMPLETE'
              : 'SESSION FAILED' }}
        </div>
        <h1>
          {{ session.status === 'expired'
            ? 'Your exam time has ended.'
            : session.status === 'completed'
              ? 'Exam session complete.'
              : 'The exam environment could not start.' }}
        </h1>
        <p>
          {{ session.status === 'expired'
            ? 'The 24-hour authorization window for this exam has ended.'
            : session.status === 'completed'
              ? 'Your dedicated exam environment has been closed.'
              : 'The environment setup failed. You can return to the catalog and try again later.' }}
        </p>

        <div class="exam-result-summary">
          <div>
            <span>SESSION</span>
            <strong>#{{ session.id }}</strong>
          </div>
          <div>
            <span>STARTED</span>
            <strong>{{ new Date(session.started_at).toLocaleString() }}</strong>
          </div>
          <div>
            <span>ENVIRONMENT</span>
            <strong>{{ session.environment?.status === 'stopped' ? 'Closed' : session.environment?.status ?? 'Unavailable' }}</strong>
          </div>
          <div>
            <span>RESULT</span>
            <strong>Score not recorded</strong>
          </div>
        </div>

        <p class="exam-result-note">
          This practice session does not currently submit task scores. Your
          session lifecycle and environment status are recorded by ExamLab.
        </p>
        <p v-if="errorMessage" class="exam-loading-error" role="alert">
          {{ errorMessage }}
        </p>
        <RouterLink to="/exams" class="primary-link">Browse exams</RouterLink>
      </template>
      <template v-else>
        <div class="catalog-eyebrow">RESULT UNAVAILABLE</div>
        <h1>We couldn't load this session.</h1>
        <p class="exam-loading-error" role="alert">{{ errorMessage }}</p>
        <RouterLink to="/exams" class="primary-link">Return to catalog</RouterLink>
      </template>
    </section>
  </main>
</template>
