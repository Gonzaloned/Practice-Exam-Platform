<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import '../assets/styles/auth.css'
import { registerAccount } from '../services/auth'

const router = useRouter()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const acceptedTerms = ref(false)

const submitted = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const showSuccessModal = ref(false)

const fullNameValid = computed(() => {
  return fullName.value.trim().length >= 10
})

const emailValid = computed(() => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())
})

const passwordValid = computed(() => {
  return password.value.length >= 8 && /\d/.test(password.value)
})

const passwordsMatch = computed(() => {
  return (
    confirmPassword.value.length > 0 &&
    password.value === confirmPassword.value
  )
})

const canSubmit = computed(() => {
  return (
    fullNameValid.value &&
    emailValid.value &&
    passwordValid.value &&
    passwordsMatch.value &&
    acceptedTerms.value
  )
})

async function register() {
  submitted.value = true
  errorMessage.value = ''

  if (!canSubmit.value) {
    return
  }

  loading.value = true

  try {
    await registerAccount({
      full_name: fullName.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    showSuccessModal.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to create your account.'
  } finally {
    loading.value = false
  }
}

function goToLogin() {
  router.push('/login')
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
            CREATE ACCOUNT
          </div>

          <h1>
            Start practicing.
          </h1>

          <p>
            Create your account and start preparing for your
            next certification.
          </p>

        </div>


        <!-- REGISTER FORM -->

        <form
          class="auth-form"
          @submit.prevent="register"
        >

          <!-- FULL NAME -->

          <label>
            Full name

            <input
              v-model="fullName"
              type="text"
              placeholder="John Smith"
              autocomplete="name"
              minlength="10"
              required
            />

            <small
              v-if="submitted && !fullName"
              class="field-error"
            >
              Required field.
            </small>

            <small
              v-else-if="submitted && !fullNameValid"
              class="field-error"
            >
              Full name must contain at least 10 characters.
            </small>

          </label>


          <!-- EMAIL -->

          <label>
            Email address

            <input
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
              required
            />

            <small
              v-if="submitted && !email"
              class="field-error"
            >
              Required field.
            </small>

            <small
              v-else-if="submitted && !emailValid"
              class="field-error"
            >
              Please enter a valid email address.
            </small>

          </label>


          <!-- PASSWORD -->

          <label>
            Password

            <input
              v-model="password"
              type="password"
              placeholder="Create a password"
              autocomplete="new-password"
              minlength="8"
              required
            />

            <small class="password-hint">
              Minimum 8 characters and at least one number.
            </small>

            <small
              v-if="submitted && !password"
              class="field-error"
            >
              Required field.
            </small>

            <small
              v-else-if="submitted && !passwordValid"
              class="field-error"
            >
              Password must contain at least 8 characters
              and one number.
            </small>

          </label>


          <!-- CONFIRM PASSWORD -->

          <label>
            Confirm password

            <input
              v-model="confirmPassword"
              type="password"
              placeholder="Repeat your password"
              autocomplete="new-password"
              required
            />

            <small
              v-if="submitted && !confirmPassword"
              class="field-error"
            >
              Required field.
            </small>

            <small
              v-else-if="submitted && !passwordsMatch"
              class="field-error"
            >
              Passwords do not match.
            </small>

          </label>


          <!-- TERMS -->

          <label class="terms-option">

            <input
              v-model="acceptedTerms"
              type="checkbox"
              required
            />

            <span>
              I agree to the
              <a href="#">
                Terms of Service
              </a>
              and
              <a href="#">
                Privacy Policy
              </a>.
            </span>

          </label>

          <small
            v-if="submitted && !acceptedTerms"
            class="field-error"
          >
            You must accept the terms.
          </small>


          <!-- API ERROR -->

          <div
            v-if="errorMessage"
            class="auth-error"
          >
            {{ errorMessage }}
          </div>


          <!-- SUBMIT -->

          <button
            type="submit"
            class="auth-submit"
            :disabled="loading"
          >
            {{ loading
              ? 'Creating account...'
              : 'Create account'
            }}
          </button>

        </form>


        <!-- DIVIDER -->

        <div class="auth-divider">
          <span>OR</span>
        </div>


        <!-- LOGIN -->

        <div class="auth-register">

          <span>
            Already have an account?
          </span>

          <RouterLink to="/login">
            Sign in
          </RouterLink>

        </div>

      </div>


      <!-- BACK -->

      <RouterLink
        to="/"
        class="auth-back"
      >
        ← Back to ExamLab
      </RouterLink>

    </div>


    <!-- SUCCESS MODAL -->

    <div
      v-if="showSuccessModal"
      class="modal-overlay"
      role="presentation"
    >

      <div
        class="success-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="success-modal-title"
        aria-describedby="success-modal-description"
      >

        <div class="success-icon">
          ✓
        </div>

        <h2 id="success-modal-title">
          Account created
        </h2>

        <p id="success-modal-description">
          Your ExamLab account has been created successfully.
          You can now sign in and start practicing.
        </p>

        <button
          class="auth-submit"
          @click="goToLogin"
        >
          Continue to sign in
        </button>

      </div>

    </div>

  </div>
</template>