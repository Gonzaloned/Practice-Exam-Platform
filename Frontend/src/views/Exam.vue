<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import '../assets/styles/exam.css'
import ExamHeader from '../components/ExamHeader.vue'
import TaskSidebar from '../components/TaskSidebar.vue'
import TaskPanel from '../components/TaskPanel.vue'
import { tasks as examTasks, type Task } from '../data/exam'
import {
  ExamSessionError,
  expireLocalLogin,
  finishAttemptData,
  setAttemptData,
  type ExamSession,
} from '../services/setAttemptData'
import {
  advanceAttemptEnvironment,
  cleanupAttemptEnvironment,
} from '../services/vmEnvironment'

const route = useRoute()
const router = useRouter()
const ExamTerminal = defineAsyncComponent(
  () => import('../components/ExamTerminal.vue')
)
const session = ref<ExamSession | null>(null)
const isLoading = ref(true)
const isFinishing = ref(false)
const errorMessage = ref('')
const now = ref(Date.now())
const tasks = ref<Task[]>(
  examTasks.map((task, index) => ({
    ...task,
    status: index === 0 ? 'current' : 'pending',
  }))
)
const selectedId = ref(tasks.value[0]?.id ?? 1)
let pollTimer: number | undefined
let clockTimer: number | undefined
let requestInProgress = false
let loadedQuestionAttemptId: number | null = null

const sessionId = computed(() => String(route.params.sessionId))
const isExamTry = computed(() => session.value?.exam_slug === 'examtry')
const examTitle = computed(() => session.value?.exam_name ?? 'Practice exam')
const examSubtitle = computed(() =>
  isExamTry.value
    ? 'Dedicated SSH practice environment'
    : 'Linux Foundation Certified System Administrator'
)
const selectedTask = computed(() =>
  tasks.value.find(task => task.id === selectedId.value) ?? tasks.value[0]
)
const completed = computed(() =>
  tasks.value.filter(task => task.status === 'done').length
)
const remainingTime = computed(() => {
  if (!session.value) {
    return '--:--:--'
  }
  const seconds = Math.max(
    0,
    Math.floor((Date.parse(session.value.expires_at) - now.value) / 1000)
  )
  const hours = String(Math.floor(seconds / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
  const remainder = String(seconds % 60).padStart(2, '0')
  return `${hours}:${minutes}:${remainder}`
})

function showLoginForExpiredToken() {
  expireLocalLogin()
  void router.replace({
    name: 'login',
    query: { redirect: route.fullPath },
  })
}

async function refreshSession() {
  if (requestInProgress) {
    return
  }
  requestInProgress = true
  try {
    const environmentData = await advanceAttemptEnvironment(sessionId.value)
    const result = await setAttemptData(sessionId.value)
    session.value = result
    session.value.environment_error = environmentData.environment_error
    if (
      result.exam_slug !== 'examtry' &&
      result.questions.length > 0 &&
      loadedQuestionAttemptId !== result.id
    ) {
      tasks.value = result.questions.map((question, index) => ({
        id: question.id,
        title: question.title,
        category: 'Exam',
        description: question.description,
        requirements: [],
        status: index === 0 ? 'current' : 'pending',
      }))
      selectedId.value = tasks.value[0]?.id ?? 1
      loadedQuestionAttemptId = result.id
    }
    errorMessage.value = ''

    if (result.status === 'completed' || result.status === 'expired') {
      await router.replace({
        name: 'exam-results',
        params: { sessionId: result.id },
      })
      return
    }
    if (result.status === 'failed') {
      errorMessage.value = environmentData.environment_error
        || 'The exam environment could not be prepared. Return to the exam details and try again.'
      return
    }
  } catch (error) {
    if (error instanceof ExamSessionError && error.status === 401) {
      showLoginForExpiredToken()
      return
    }
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to check the exam environment.'
  } finally {
    isLoading.value = false
    requestInProgress = false
  }
}

function selectTask(id: number) {
  selectedId.value = id
  tasks.value = tasks.value.map(task => ({
    ...task,
    status: task.id === id ? 'current' : task.status === 'done' ? 'done' : 'pending',
  }))
}

async function endExam() {
  if (isFinishing.value) {
    return
  }

  isFinishing.value = true
  errorMessage.value = ''
  try {
    const result = await finishAttemptData(sessionId.value)
    await cleanupAttemptEnvironment(result.id)
    await router.replace({
      name: 'exam-results',
      params: { sessionId: result.id },
    })
  } catch (error) {
    if (error instanceof ExamSessionError && error.status === 401) {
      showLoginForExpiredToken()
      return
    }
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to finish the exam session.'
    await refreshSession()
  } finally {
    isFinishing.value = false
  }
}

onMounted(() => {
  void refreshSession()
  pollTimer = window.setInterval(() => void refreshSession(), 3000)
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer)
  }
  if (clockTimer !== undefined) {
    window.clearInterval(clockTimer)
  }
})
</script>

<template>
  <div v-if="session?.status === 'running' && session.environment?.status === 'ready'" class="app-shell">
    <ExamHeader
      :exam-title="examTitle"
      :exam-subtitle="examSubtitle"
      :show-progress="!isExamTry"
      :completed="completed"
      :total="tasks.length"
      :remaining-time="remainingTime"
      :is-finishing="isFinishing"
      @finish="endExam"
    />

    <main v-if="isExamTry" class="examtry-session-layout">
      <section class="examtry-session-intro">
        <div class="examtry-session-eyebrow">ATTEMPT #{{ session.id }}</div>
        <h1>ExamTry workspace</h1>
        <p>Your snapshot-backed VM is ready. Use the SSH terminal below.</p>
      </section>
      <ExamTerminal :attempt-id="session.id" />
    </main>

    <main v-else class="exam-layout">
      <TaskSidebar
        exam-title="LFCS — Linux Administration"
        :tasks="tasks"
        :selected-id="selectedId"
        @select="selectTask"
      />
      <TaskPanel v-if="selectedTask" :task="selectedTask" />
      <ExamTerminal :attempt-id="session.id" />
    </main>
    <div v-if="errorMessage" class="exam-session-error" role="alert">
      {{ errorMessage }}
    </div>
  </div>

  <main v-else class="exam-loading-page">
    <section class="exam-loading-card" aria-live="polite">
      <div
        v-if="!errorMessage && (isLoading || session?.status === 'provisioning')"
        class="exam-loader"
        aria-hidden="true"
      ></div>
      <div class="catalog-eyebrow">
        {{ errorMessage ? 'ENVIRONMENT STATUS' : 'PREPARING YOUR SESSION' }}
      </div>
      <h1>
        {{ errorMessage ? 'We could not prepare your exam.' : 'Getting your lab ready.' }}
      </h1>
      <p v-if="errorMessage" class="exam-loading-error" role="alert">
        {{ errorMessage }}
      </p>
      <p v-else>
        Your dedicated environment is being checked. This page will continue
        automatically when it is ready.
      </p>
      <div v-if="session" class="exam-loading-status">
        <span class="exam-loading-status-dot"></span>
        {{ session.environment?.status === 'ready' ? 'Environment ready' : 'Provisioning the exam environment' }}
      </div>
      <RouterLink
        v-if="errorMessage"
        :to="session?.exam_slug === 'examtry' ? '/examtry' : '/exams/lfcs'"
        class="primary-link"
      >
        Return to exam details
      </RouterLink>
      <button
        v-else
        type="button"
        class="exam-loading-cancel"
        @click="router.push('/exams')"
      >
        Leave this page
      </button>
    </section>
  </main>
</template>

<style scoped>
.examtry-session-layout {
  min-height: calc(100vh - 72px);
  padding: clamp(1.25rem, 4vw, 3rem);
}

.examtry-session-intro {
  max-width: 70rem;
  margin: 0 auto;
  color: #e8edf5;
}

.examtry-session-eyebrow {
  color: #8cae92;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.examtry-session-intro h1 {
  margin: 0.5rem 0;
  font-size: clamp(1.5rem, 4vw, 2.25rem);
}

.examtry-session-intro p {
  color: #aeb8c7;
}
</style>
