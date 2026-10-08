<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppNavBar from '../components/AppNavBar.vue'
import {
  createProxmoxSocket,
  ProxmoxConsoleError,
  sendProxmoxCommand,
  type ProxmoxVm,
} from '../services/proxmoxConsole'
import type { Socket } from 'socket.io-client'

interface ConsoleLine {
  id: number
  kind: 'input' | 'output' | 'error'
  text: string
}

const router = useRouter()
const commandInput = ref('')
const isBusy = ref(false)
const isSocketConnected = ref(false)
const socketStatus = ref('Connecting to Flask…')
const lines = ref<ConsoleLine[]>([
  {
    id: 0,
    kind: 'output',
    text: 'ExamTry Proxmox API console. Type "help" for available commands.',
  },
])
const vmList = ref<ProxmoxVm[]>([])
const nextLineId = ref(1)
const terminalBody = ref<HTMLElement | null>(null)
let proxmoxSocket: Socket | null = null

function writeLine(kind: ConsoleLine['kind'], text: string) {
  lines.value.push({ id: nextLineId.value++, kind, text })
  void nextTick(() => {
    terminalBody.value?.scrollTo({ top: terminalBody.value.scrollHeight })
  })
}

function formatVmList(vms: ProxmoxVm[]) {
  if (vms.length === 0) {
    return 'No QEMU VMs were returned for the configured Proxmox node.'
  }
  return vms
    .map((vm) => `${vm.vmid}  ${vm.status ?? 'unknown'}  ${vm.name ?? '(unnamed)'}`)
    .join('\n')
}

function getProxmoxSocket(): Socket {
  if (!proxmoxSocket) {
    throw new ProxmoxConsoleError('The Flask socket is not connected.', 0)
  }
  return proxmoxSocket
}

async function executeCommand(rawCommand: string) {
  const [command, argument, ...extra] = rawCommand.trim().split(/\s+/)
  if (!command) return
  if (extra.length > 0) {
    throw new Error('Use one command and at most one VM ID.')
  }

  switch (command.toLowerCase()) {
    case 'help':
      writeLine(
        'output',
        [
          'connect              Test Flask-to-Proxmox API access',
          'vms                  List QEMU VMs on the configured node',
          'status <vmid>        Get the current VM status',
          'start <vmid>         Start an allowlisted VM',
          'stop <vmid>          Stop an allowlisted VM',
          'help                 Show these commands',
        ].join('\n')
      )
      return
    case 'connect': {
      if (argument) throw new Error('Usage: connect')
      const result = await sendProxmoxCommand(getProxmoxSocket(), 'connect')
      writeLine(
        'output',
        `Connected to node ${result.node}. Proxmox ${result.version?.version ?? 'version unavailable'}.`
      )
      return
    }
    case 'vms': {
      if (argument) throw new Error('Usage: vms')
      const result = await sendProxmoxCommand(getProxmoxSocket(), 'vms')
      vmList.value = result.vms ?? []
      writeLine('output', `Node ${result.node}\n${formatVmList(vmList.value)}`)
      return
    }
    case 'status':
    case 'start':
    case 'stop': {
      if (!argument || !/^\d+$/.test(argument) || Number(argument) < 1) {
        throw new Error(`Usage: ${command.toLowerCase()} <vmid>`)
      }
      const vmid = Number(argument)
      const action = command.toLowerCase()
      if (action === 'status') {
        const result = await sendProxmoxCommand(getProxmoxSocket(), 'status', vmid)
        writeLine('output', JSON.stringify(result.vm, null, 2))
      } else if (action === 'start' || action === 'stop') {
        const result = await sendProxmoxCommand(
          getProxmoxSocket(),
          action,
          vmid
        )
        writeLine(
          'output',
          `${result.message}${result.task_id ? ` UPID: ${result.task_id}` : ''}`
        )
      } else {
        throw new Error(`Unsupported command "${action}".`)
      }
      return
    }
    default:
      throw new Error(`Unknown command "${command}". Type "help" for available commands.`)
  }
}

async function submitCommand() {
  const command = commandInput.value.trim()
  if (!command || isBusy.value) return
  commandInput.value = ''
  writeLine('input', `> ${command}`)
  isBusy.value = true

  try {
    await executeCommand(command)
  } catch (error) {
    if (
      error instanceof ProxmoxConsoleError &&
      error.status === 401
    ) {
      await router.push({
        name: 'login',
        query: { redirect: '/examtry' },
      })
      return
    }
    writeLine(
      'error',
      error instanceof Error ? error.message : 'The command failed.'
    )
  } finally {
    isBusy.value = false
  }
}

async function runQuickCommand(command: string) {
  commandInput.value = command
  await submitCommand()
}

onMounted(() => {
  const token = localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token')
  if (!token) {
    void router.push({ name: 'login', query: { redirect: '/examtry' } })
    return
  }

  proxmoxSocket = createProxmoxSocket(token)
  proxmoxSocket.on('connect', () => {
    isSocketConnected.value = true
    socketStatus.value = 'Connected to Flask'
  })
  proxmoxSocket.on('disconnect', () => {
    isSocketConnected.value = false
    socketStatus.value = 'Disconnected from Flask'
  })
  proxmoxSocket.on('connect_error', (error: Error) => {
    isSocketConnected.value = false
    socketStatus.value = 'Flask connection failed'
    writeLine('error', error.message || 'Could not open the Flask socket.')
  })
  proxmoxSocket.connect()
})

onUnmounted(() => {
  proxmoxSocket?.disconnect()
  proxmoxSocket = null
})
</script>

<template>
  <div class="examtry-page">
    <AppNavBar />

    <main class="examtry-main">
      <header class="examtry-heading">
        <div>
          <div class="examtry-eyebrow">PROXMOX INTEGRATION</div>
          <h1>ExamTry console</h1>
          <p>Send approved API operations through Flask to your configured Proxmox node.</p>
        </div>
        <span class="examtry-connection-indicator">
          <span :class="{ 'is-connected': isSocketConnected }" aria-hidden="true"></span>
          {{ socketStatus }}
        </span>
      </header>

      <section class="examtry-panel">
        <div class="examtry-panel-heading">
          <div>
            <div class="examtry-eyebrow">COMMAND CONSOLE</div>
            <h2>Proxmox API</h2>
          </div>
          <div class="examtry-quick-actions">
            <button type="button" :disabled="isBusy" @click="runQuickCommand('connect')">
              Test connection
            </button>
            <button type="button" :disabled="isBusy" @click="runQuickCommand('vms')">
              List VMs
            </button>
          </div>
        </div>

        <div
          ref="terminalBody"
          class="examtry-terminal"
          role="log"
          aria-live="polite"
          aria-label="Proxmox API command output"
        >
          <div
            v-for="line in lines"
            :key="line.id"
            class="examtry-terminal-line"
            :class="`is-${line.kind}`"
          >{{ line.text }}</div>
          <div v-if="isBusy" class="examtry-terminal-line is-output">
            <span class="examtry-spinner" aria-hidden="true"></span>
            Waiting for Flask / Proxmox...
          </div>
        </div>

        <form class="examtry-command-form" @submit.prevent="submitCommand">
          <label for="examtry-command">&gt;</label>
          <input
            id="examtry-command"
            v-model="commandInput"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="Type help, connect, vms, status 100, start 100..."
            :disabled="isBusy"
          />
          <button type="submit" :disabled="isBusy || !commandInput.trim()">
            {{ isBusy ? 'Running…' : 'Run' }}
          </button>
        </form>
      </section>

      <section v-if="vmList.length" class="examtry-panel examtry-vm-panel">
        <div class="examtry-panel-heading">
          <div>
            <div class="examtry-eyebrow">NODE INVENTORY</div>
            <h2>QEMU virtual machines</h2>
          </div>
        </div>
        <div class="examtry-vm-list">
          <div v-for="vm in vmList" :key="vm.vmid" class="examtry-vm-row">
            <div>
              <strong>{{ vm.name || `VM ${vm.vmid}` }}</strong>
              <span>VMID {{ vm.vmid }}</span>
            </div>
            <span class="examtry-vm-status">{{ vm.status || 'unknown' }}</span>
            <div class="examtry-vm-actions">
              <button type="button" :disabled="isBusy" @click="runQuickCommand(`status ${vm.vmid}`)">
                Status
              </button>
              <button type="button" :disabled="isBusy" @click="runQuickCommand(`start ${vm.vmid}`)">
                Start
              </button>
              <button type="button" :disabled="isBusy" @click="runQuickCommand(`stop ${vm.vmid}`)">
                Stop
              </button>
            </div>
          </div>
        </div>
        <p class="examtry-note">
          Start/stop is restricted to the VM IDs configured in Flask.
        </p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.examtry-page {
  min-height: 100vh;
  background: #090b10;
  color: #e8edf5;
}

.examtry-main {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
  padding: 64px 0 80px;
}

.examtry-heading,
.examtry-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.examtry-heading {
  margin-bottom: 30px;
}

.examtry-eyebrow {
  color: #86a7ff;
  font: 500 11px/1.4 "DM Mono", monospace;
  letter-spacing: .12em;
}

.examtry-heading h1,
.examtry-panel h2 {
  margin: 8px 0;
  letter-spacing: -.035em;
}

.examtry-heading h1 {
  font-size: clamp(32px, 5vw, 46px);
}

.examtry-heading p,
.examtry-note {
  margin: 0;
  color: #9da8b9;
  line-height: 1.6;
}

.examtry-connection-indicator {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: 1px solid #252d3b;
  border-radius: 999px;
  padding: 9px 13px;
  color: #b5c0d0;
  font-size: 12px;
  white-space: nowrap;
}

.examtry-connection-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e7b35d;
}

.examtry-connection-indicator span.is-connected {
  background: #58cb91;
}

.examtry-panel {
  margin-top: 20px;
  padding: 24px;
  border: 1px solid #222a36;
  border-radius: 16px;
  background: #0e121a;
}

.examtry-panel h2 {
  font-size: 20px;
}

.examtry-quick-actions,
.examtry-vm-actions {
  display: flex;
  gap: 8px;
}

.examtry-quick-actions button,
.examtry-vm-actions button,
.examtry-command-form button {
  border: 1px solid #303949;
  border-radius: 8px;
  padding: 9px 12px;
  background: #171e2a;
  color: #dbe4f2;
  cursor: pointer;
}

.examtry-quick-actions button:hover,
.examtry-vm-actions button:hover {
  background: #202a39;
}

.examtry-quick-actions button:disabled,
.examtry-vm-actions button:disabled,
.examtry-command-form button:disabled {
  opacity: .55;
  cursor: not-allowed;
}

.examtry-terminal {
  min-height: 280px;
  max-height: 460px;
  overflow: auto;
  margin-top: 20px;
  padding: 18px;
  border: 1px solid #242b36;
  border-radius: 10px 10px 0 0;
  background: #07090d;
  font: 13px/1.65 "DM Mono", monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.examtry-terminal-line {
  margin: 0 0 5px;
}

.examtry-terminal-line.is-input {
  color: #91b4ff;
}

.examtry-terminal-line.is-output {
  color: #c1cbd9;
}

.examtry-terminal-line.is-error {
  color: #ff8585;
}

.examtry-command-form {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #242b36;
  border-top: 0;
  border-radius: 0 0 10px 10px;
  padding: 10px 12px;
  background: #0a0d12;
  color: #91b4ff;
  font: 14px "DM Mono", monospace;
}

.examtry-command-form input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: #e8edf5;
  font: inherit;
}

.examtry-command-form button {
  color: #fff;
}

.examtry-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 7px;
  border: 1px solid #71809a;
  border-top-color: #91b4ff;
  border-radius: 50%;
  animation: examtry-spin .8s linear infinite;
}

.examtry-vm-list {
  margin-top: 14px;
}

.examtry-vm-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 100px auto;
  align-items: center;
  gap: 16px;
  border-top: 1px solid #222a36;
  padding: 14px 0;
}

.examtry-vm-row > div:first-child {
  display: grid;
  gap: 4px;
}

.examtry-vm-row > div:first-child span,
.examtry-vm-status {
  color: #9da8b9;
  font-size: 12px;
}

.examtry-vm-status {
  text-transform: capitalize;
}

.examtry-note {
  margin-top: 8px;
  font-size: 12px;
}

@keyframes examtry-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 680px) {
  .examtry-main {
    width: min(100% - 24px, 1120px);
    padding-top: 36px;
  }

  .examtry-heading,
  .examtry-panel-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .examtry-panel {
    padding: 16px;
  }

  .examtry-vm-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .examtry-vm-actions {
    grid-column: 1 / -1;
  }
}
</style>
