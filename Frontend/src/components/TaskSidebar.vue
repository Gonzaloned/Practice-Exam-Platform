<template>
  <aside class="sidebar">
    <div class="sidebar-title">
      <div>
        <span class="eyebrow">PRACTICE EXAM</span>
        <h2>{{ examTitle }}</h2>
      </div>
      <span class="task-count">{{ tasks.length }} tasks</span>
    </div>

    <div class="task-list">
      <button
        v-for="task in tasks"
        :key="task.id"
        class="task-item"
        :class="{ active: task.id === selectedId }"
        @click="$emit('select', task.id)"
      >
        <span class="task-number" :class="task.status">
          <span v-if="task.status === 'done'">✓</span>
          <span v-else>{{ String(task.id).padStart(2, '0') }}</span>
        </span>
        <span class="task-info">
          <strong>{{ task.title }}</strong>
          <small>{{ task.category }}</small>
        </span>
        <span v-if="task.status === 'current'" class="current-dot"></span>
      </button>
    </div>

    <div class="sidebar-footer">
      <div class="legend"><span class="legend-dot done"></span> Completed</div>
      <div class="legend"><span class="legend-dot current"></span> Current</div>
      <div class="legend"><span class="legend-dot pending"></span> Pending</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { Task } from '../data/exam'

defineProps<{
  examTitle: string
  tasks: Task[]
  selectedId: number
}>()

defineEmits<{
  select: [id: number]
}>()
</script>
