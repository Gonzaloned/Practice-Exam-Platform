<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import '../assets/styles/exam.css'
import ExamHeader from '../components/ExamHeader.vue'
import TaskSidebar from '../components/TaskSidebar.vue'
import TaskPanel from '../components/TaskPanel.vue'
import { tasks as examTasks, type Task } from '../data/exam'
import {
  ExamSessionError,
  expireLocalLogin,
  finishExamSession,
  getExamSession,
  type ExamSession,
} from '../services/examSessions'

const route = useRoute()
const router = useRouter()
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

const sessionId = computed(() => String(route.params.sessionId))
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
    const result = await getExamSession(sessionId.value)
    session.value = result
    errorMessage.value = ''

    if (result.status === 'completed' || result.status === 'expired') {
      await router.replace({
        name: 'exam-results',
        params: { sessionId: result.id },
      })
      return
    }
    if (result.status === 'failed') {
      errorMessage.value = 'The exam environment could not be prepared. Return to the exam details and try again.'
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
    const result = await finishExamSession(sessionId.value)
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
      :completed="completed"
      :total="tasks.length"
      :remaining-time="remainingTime"
      :is-finishing="isFinishing"
      @finish="endExam"
    />

    <main class="exam-layout">
      <TaskSidebar
        :tasks="tasks"
        :selected-id="selectedId"
        @select="selectTask"
      />
      <TaskPanel v-if="selectedTask" :task="selectedTask" />
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
      <RouterLink v-if="errorMessage" to="/exams/lfcs" class="primary-link">
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
