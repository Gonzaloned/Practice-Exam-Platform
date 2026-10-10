<template>
  <header class="exam-header">
    <div class="brand">
      <div class="brand-mark">L</div>
      <div>
        <div class="brand-name">{{ examTitle }}</div>
        <div class="brand-subtitle">{{ examSubtitle }}</div>
      </div>
    </div>

    <div class="exam-meta">
      <div class="progress-wrap">
        <template v-if="showProgress">
          <span>Progress</span>
          <strong>{{ completed }}/{{ total }}</strong>
        </template>
      </div>
      <div class="timer">
        <span class="timer-dot"></span>
        {{ remainingTime }}
      </div>
      <button
        class="finish-btn"
        :disabled="isFinishing"
        @click="$emit('finish')"
      >
        {{ isFinishing ? 'Finishing...' : 'Finish exam' }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  examTitle: string
  examSubtitle: string
  showProgress: boolean
  completed: number
  total: number
  remainingTime: string
  isFinishing: boolean
}>()

defineEmits<{
  finish: []
}>()
</script>
