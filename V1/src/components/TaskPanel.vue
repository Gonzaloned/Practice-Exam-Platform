<template>
  <section class="workspace">
    <div class="task-heading">
      <div>
        <div class="breadcrumb">
          Task {{ String(task.id).padStart(2, '0') }}
          <span>/</span>
          {{ task.category }}
        </div>
        <h1>{{ task.title }}</h1>
      </div>
      <div class="task-state" :class="task.status">
        <span></span>
        {{ task.status === 'current' ? 'In progress' : task.status === 'done' ? 'Completed' : 'Not started' }}
      </div>
    </div>

    <div class="description-card">
      <div class="card-label">TASK</div>
      <p>{{ task.description }}</p>

      <div class="requirements">
        <div class="card-label">REQUIREMENTS</div>
        <ul>
          <li v-for="item in task.requirements" :key="item">
            <span class="requirement-bullet">•</span>{{ item }}
          </li>
        </ul>
      </div>
    </div>

    <div class="terminal-card">
      <div class="terminal-toolbar">
        <div class="terminal-title">
          <span class="terminal-status"></span>
          lab-ubuntu
        </div>
        <div class="terminal-actions">
          <span>SSH session</span>
          <button>⌗</button>
          <button>•••</button>
        </div>
      </div>

      <div class="terminal">
        <div><span class="prompt">root@lfcs-lab</span><span class="colon">:</span><span class="path">~</span><span class="symbol">#</span> <span>ls</span></div>
        <div class="output">bin  boot  dev  etc  home  lib  media  mnt  opt  proc  root  run  srv  tmp  usr  var</div>
        <div class="spacer"></div>
        <div><span class="prompt">root@lfcs-lab</span><span class="colon">:</span><span class="path">~</span><span class="symbol">#</span> <span class="cursor">█</span></div>
      </div>
    </div>

    <div class="workspace-footer">
      <div class="hint">
        <span class="hint-icon">i</span>
        Complete the task on the lab machine, then verify your work.
      </div>
      <button class="check-btn">
        Check task
        <span>→</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Task } from '../data/exam'

defineProps<{
  task: Task
}>()
</script>
