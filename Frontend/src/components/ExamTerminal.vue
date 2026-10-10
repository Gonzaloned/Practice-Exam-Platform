<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'
import {
  connectAttemptSsh,
  createAttemptSshConnection,
} from '../services/sshAttemptConnection'
import {
  listenSshConsole,
  resizeSshConsole,
  sendSshConsoleInput,
} from '../services/sshConsoleFlow'
import type { Socket } from 'socket.io-client'

const props = defineProps<{
  attemptId: number
}>()

const terminalElement = ref<HTMLElement | null>(null)
const connectionStatus = ref('Connecting to terminal service…')
let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let socket: Socket | null = null
let stopListening: (() => void) | null = null

function fitTerminal() {
  if (!terminal || !fitAddon) {
    return
  }
  fitAddon.fit()
  if (socket?.connected) {
    resizeSshConsole(socket, terminal.cols, terminal.rows)
  }
}

onMounted(() => {
  if (!terminalElement.value) {
    return
  }
  terminal = new Terminal({
    cursorBlink: true,
    convertEol: true,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    fontSize: 14,
    theme: {
      background: '#101820',
      foreground: '#e5edf4',
      cursor: '#71d4a5',
    },
  })
  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalElement.value)
  fitTerminal()
  terminal.write('Opening your exam VM terminal…\r\n')
  terminal.onData((data) => {
    if (socket?.connected) {
      sendSshConsoleInput(socket, data)
    }
  })
  terminal.onResize(({ cols, rows }) => {
    if (socket?.connected) {
      resizeSshConsole(socket, cols, rows)
    }
  })
  window.addEventListener('resize', fitTerminal)

  const token = localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token')
  if (!token) {
    connectionStatus.value = 'Sign in to open the terminal.'
    terminal.writeln('\r\nAuthentication is required.')
    return
  }

  socket = createAttemptSshConnection(token)
  stopListening = listenSshConsole(socket, {
    data: data => terminal?.write(data),
    error: message => {
      connectionStatus.value = 'Terminal disconnected'
      terminal?.writeln(`\r\n${message}`)
    },
    closed: () => {
      connectionStatus.value = 'Terminal closed'
    },
  })
  socket.on('connect', () => {
    connectionStatus.value = 'Connecting to your main VM…'
    if (!socket) {
      return
    }
    void connectAttemptSsh(socket, props.attemptId)
      .then(() => {
        connectionStatus.value = 'Connected to the main VM'
        fitTerminal()
        terminal?.focus()
      })
      .catch((error: unknown) => {
        const message = error instanceof Error
          ? error.message
          : 'Could not open the SSH terminal.'
        connectionStatus.value = 'Terminal unavailable'
        terminal?.writeln(`\r\n${message}`)
      })
  })
  socket.on('disconnect', () => {
    connectionStatus.value = 'Disconnected from terminal service'
  })
  socket.on('connect_error', (error: Error) => {
    connectionStatus.value = 'Terminal service unavailable'
    terminal?.writeln(`\r\n${error.message}`)
  })
  socket.connect()
})

onUnmounted(() => {
  window.removeEventListener('resize', fitTerminal)
  stopListening?.()
  stopListening = null
  socket?.disconnect()
  socket = null
  terminal?.dispose()
  terminal = null
  fitAddon = null
})
</script>

<template>
  <section class="exam-terminal-panel">
    <header class="exam-terminal-header">
      <div>
        <div class="exam-terminal-eyebrow">MAIN EXAM VM</div>
        <h2>Ubuntu terminal</h2>
      </div>
      <span class="exam-terminal-status" role="status">{{ connectionStatus }}</span>
    </header>
    <div ref="terminalElement" class="exam-terminal-screen" aria-label="SSH terminal"></div>
  </section>
</template>

<style scoped>
.exam-terminal-panel {
  grid-column: 1 / -1;
  margin: 1.5rem;
  overflow: hidden;
  border: 1px solid #d7e0e8;
  border-radius: 1rem;
  background: #fff;
}

.exam-terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #d7e0e8;
}

.exam-terminal-eyebrow {
  color: #607487;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.exam-terminal-header h2 {
  margin: 0.25rem 0 0;
  color: #152b3c;
  font-size: 1rem;
}

.exam-terminal-status {
  color: #52697a;
  font-size: 0.85rem;
  text-align: right;
}

.exam-terminal-screen {
  height: min(42vh, 28rem);
  min-height: 16rem;
  padding: 0.75rem;
  background: #101820;
}
</style>
