<template>
  <div class="app-shell">
    <ExamHeader :completed="completed" :total="tasks.length" />

    <main class="exam-layout">
      <TaskSidebar
        :tasks="tasks"
        :selected-id="selectedId"
        @select="selectedId = $event"
      />
      <TaskPanel :task="selectedTask" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import '../assets/styles/exam.css'
import ExamHeader from '../components/ExamHeader.vue'
import TaskSidebar from '../components/TaskSidebar.vue'
import TaskPanel from '../components/TaskPanel.vue'
import { tasks } from '../data/exam.ts'

const selectedId = ref(4)
const selectedTask = computed(() => tasks.find(task => task.id === selectedId.value) ?? tasks[0])
const completed = computed(() => tasks.filter(task => task.status === 'done').length)
</script>
