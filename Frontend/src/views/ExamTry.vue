<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppNavBar from '../components/AppNavBar.vue'
import { createAttemptForExam } from '../services/attemptCreate'
import { ExamSessionError } from '../services/attemptTypes'
import { expireLocalLogin } from '../services/setAttemptData'

const router = useRouter()
const isStarting = ref(false)
const errorMessage = ref('')

async function startExamTry() {
  if (isStarting.value) {
    return
  }

  isStarting.value = true
  errorMessage.value = ''
  try {
    const attempt = await createAttemptForExam('examtry')
    await router.replace({
      name: 'exam-session',
      params: { sessionId: attempt.id },
    })
  } catch (error) {
    if (error instanceof ExamSessionError && error.status === 401) {
      expireLocalLogin()
      await router.replace({
        name: 'login',
        query: { redirect: '/examtry' },
      })
      return
    }
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Could not start the ExamTry environment.'
  } finally {
    isStarting.value = false
  }
}
</script>

<template>
  <div class="examtry-page">
    <AppNavBar />
    <main class="examtry-main">
      <section class="examtry-card">
        <div class="examtry-eyebrow">PRACTICE EXAM</div>
        <h1>ExamTry</h1>
        <p>
          Start a dedicated virtual machine from snapshot 901. When it is ready,
          the exam page opens a secure SSH terminal through Flask.
        </p>
        <p v-if="errorMessage" class="examtry-error" role="alert">
          {{ errorMessage }}
        </p>
        <div class="examtry-actions">
          <button
            type="button"
            class="examtry-start"
            :disabled="isStarting"
            @click="startExamTry"
          >
            {{ isStarting ? 'Starting ExamTry…' : 'Start ExamTry' }}
          </button>
          <RouterLink to="/exams" class="examtry-back">Back to exams</RouterLink>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.examtry-page {
  min-height: 100vh;
  background: #f3f6f8;
}

.examtry-main {
  display: grid;
  min-height: calc(100vh - 4rem);
  place-items: center;
  padding: 2rem 1rem;
}

.examtry-card {
  width: min(100%, 38rem);
  padding: clamp(1.5rem, 5vw, 3rem);
  border: 1px solid #d7e0e8;
  border-radius: 1rem;
  background: #fff;
  box-shadow: 0 1rem 3rem rgb(21 43 60 / 8%);
}

.examtry-eyebrow {
  color: #607487;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.examtry-card h1 {
  margin: 0.75rem 0;
  color: #152b3c;
  font-size: clamp(2rem, 7vw, 3rem);
}

.examtry-card p {
  color: #52697a;
  line-height: 1.65;
}

.examtry-card .examtry-error {
  color: #a32929;
}

.examtry-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.examtry-start {
  padding: 0.8rem 1.25rem;
  border: 0;
  border-radius: 0.6rem;
  background: #176b50;
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.examtry-start:disabled {
  cursor: wait;
  opacity: 0.7;
}

.examtry-back {
  color: #31566f;
  font-weight: 600;
}
</style>
