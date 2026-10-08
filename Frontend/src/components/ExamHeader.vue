<template>
  <header class="exam-header">
    <div class="brand">
      <div class="brand-mark">L</div>
      <div>
        <div class="brand-name">LFCS Practice</div>
        <div class="brand-subtitle">Linux Foundation Certified System Administrator</div>
      </div>
    </div>

    <div class="exam-meta">
      <div class="progress-wrap">
        <span>Progress</span>
        <strong>{{ completed }}/{{ total }}</strong>
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
  completed: number
  total: number
  remainingTime: string
  isFinishing: boolean
}>()

defineEmits<{
  finish: []
}>()
</script>
