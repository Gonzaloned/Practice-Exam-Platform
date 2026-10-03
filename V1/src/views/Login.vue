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
            ACCOUNT ACCESS
          </div>

          <h1>
            Welcome back.
          </h1>

          <p>
            Sign in to continue your certification practice.
          </p>

        </div>


        <form class="auth-form">

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
              placeholder="Enter your password"
              autocomplete="current-password"
            />
          </label>


          <div class="auth-options">

            <label class="remember-option">

              <input type="checkbox" />

              <span>
                Remember me
              </span>

            </label>

            <a href="#">
              Forgot password?
            </a>

          </div>


          <button
            type="submit"
            class="auth-submit"
          >
            Sign in
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