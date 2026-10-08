<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import '../assets/styles/auth.css'
import { loginAccount } from '../services/auth'

const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const rememberMe = ref(false)
const loading = ref(false)
const errorMessage = ref('')

async function login() {
  errorMessage.value = ''
  loading.value = true

  try {
    const { accessToken } = await loginAccount({
      email: email.value.trim(),
      password: password.value,
    })

    if (rememberMe.value) {
      localStorage.setItem('access_token', accessToken)
      sessionStorage.removeItem('access_token')
    } else {
      sessionStorage.setItem('access_token', accessToken)
      localStorage.removeItem('access_token')
    }

    const redirect = route.query.redirect
    const destination = typeof redirect === 'string' &&
      redirect.startsWith('/') &&
      !redirect.startsWith('//') &&
      !redirect.includes('\\')
      ? redirect
      : '/'
    await router.push(destination)
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to sign in. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">

    <div class="auth-container">

      <!-- BRAND -->

      <RouterLink to="/" class="auth-brand">

        <div class="brand-mark">
          E
        </div>

        <div>
          <div class="brand-name">
            ExamLab
          </div>

          <div class="brand-subtitle">
            Certification Practice
          </div>
        </div>

      </RouterLink>


      <!-- CARD -->

      <div class="auth-card">

        <div class="auth-header">

          <div class="auth-eyebrow">
            ACCOUNT ACCESS
          </div>

          <h1>
            Welcome back.
          </h1>

          <p>
            Sign in to continue your certification practice.
          </p>

        </div>


        <form
          class="auth-form"
          @submit.prevent="login"
        >

          <label>
            Email address

            <input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              required
            />
          </label>


          <label>
            Password

            <input
              v-model="password"
              type="password"
              placeholder="Enter your password"
              autocomplete="current-password"
              required
            />
          </label>


          <div class="auth-options">

            <label class="remember-option">

              <input
                v-model="rememberMe"
                type="checkbox"
              />

              <span>
                Remember me
              </span>

            </label>

            <a href="#">
              Forgot password?
            </a>

          </div>

          <div
            v-if="errorMessage"
            class="auth-error"
            role="alert"
          >
            {{ errorMessage }}
          </div>

          <button
            type="submit"
            class="auth-submit"
            :disabled="loading"
          >
            {{ loading ? 'Signing in...' : 'Sign in' }}
          </button>

        </form>


        <div class="auth-divider">
          <span>OR</span>
        </div>


        <div class="auth-register">

          <span>
            Don't have an account?
          </span>

          <RouterLink to="/register">
            Create one
          </RouterLink>

        </div>

      </div>


      <RouterLink
        to="/"
        class="auth-back"
      >
        ← Back to ExamLab
      </RouterLink>

    </div>

  </div>
</template>