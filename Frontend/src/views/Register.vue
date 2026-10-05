<script setup lang="ts">
import '../assets/styles/auth.css'
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


        <form class="auth-form">

          <label>
            Full name

            <input
              type="text"
              placeholder="John Smith"
              autocomplete="name"
            />
          </label>


          <label>
            Email address

            <input
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
            />
          </label>


          <label>
            Password

            <input
              type="password"
              placeholder="Create a password"
              autocomplete="new-password"
            />
          </label>


          <label>
            Confirm password

            <input
              type="password"
              placeholder="Repeat your password"
              autocomplete="new-password"
            />
          </label>


          <label class="terms-option">

            <input type="checkbox" />

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


          <button
            type="submit"
            class="auth-submit"
          >
            Create account
          </button>

        </form>


        <div class="auth-divider">
          <span>OR</span>
        </div>


        <div class="auth-register">

          <span>
            Already have an account?
          </span>

          <RouterLink to="/login">
            Sign in
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