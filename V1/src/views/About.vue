<script setup lang="ts">
import '../assets/styles/about.css'
</script>

<template>
  <div class="public-page">

    <!-- NAVBAR -->
    <header class="main-navbar">

      <RouterLink to="/" class="brand">
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

      <nav>
        <RouterLink to="/">
          Exams
        </RouterLink>

        <RouterLink to="/about" class="active">
          About
        </RouterLink>

        <RouterLink to="/login" class="login-link">
          Sign in
        </RouterLink>
      </nav>

    </header>


    <!-- HERO -->
    <main class="about-page">

      <section class="about-hero">

        <div class="about-eyebrow">
          ABOUT EXAMLAB
        </div>

        <h1>
          A simpler way to prepare
          for IT certifications.
        </h1>

        <p>
          ExamLab provides a focused practice environment
          designed to help you prepare for technical
          certification exams with confidence.
        </p>

      </section>


      <!-- OUR APPROACH -->
      <section class="about-section">

        <div class="about-section-label">
          01 / OUR APPROACH
        </div>

        <div class="about-section-content">

          <h2>
            Practice should feel
            like the real thing.
          </h2>

          <p>
            Studying documentation and understanding the theory
            are only part of the preparation process.
          </p>

          <p>
            ExamLab focuses on the experience of actually taking
            an exam: navigating tasks, managing your time,
            solving problems and staying focused.
          </p>

        </div>

      </section>


      <!-- PLATFORM -->
      <section class="about-section">

        <div class="about-section-label">
          02 / THE PLATFORM
        </div>

        <div class="about-features">

          <article class="about-feature">

            <div class="feature-number">
              01
            </div>

            <h3>
              Realistic environments
            </h3>

            <p>
              Practice in an interface designed to reproduce
              the experience of a technical certification exam.
            </p>

          </article>


          <article class="about-feature">

            <div class="feature-number">
              02
            </div>

            <h3>
              Focused preparation
            </h3>

            <p>
              Practice by certification and concentrate on
              the skills and knowledge you need to improve.
            </p>

          </article>


          <article class="about-feature">

            <div class="feature-number">
              03
            </div>

            <h3>
              No distractions
            </h3>

            <p>
              A clean and focused environment built around
              one goal: completing your exam.
            </p>

          </article>

        </div>

      </section>


      <!-- TECHNOLOGY -->
      <section class="about-section about-technology">

        <div class="about-section-label">
          03 / TECHNOLOGY
        </div>

        <div class="technology-card">

          <div class="terminal-toolbar">

            <div class="terminal-title">
              <span class="terminal-status"></span>
              examlab
            </div>

            <div class="terminal-actions">
              PLATFORM
            </div>

          </div>

          <div class="technology-content">

            <div class="tech-line">
              <span class="prompt">$</span>
              examlab --environment
            </div>

            <div class="tech-output">
              certification practice environment
            </div>

            <div class="tech-line">
              <span class="prompt">$</span>
              examlab --focus
            </div>

            <div class="tech-output">
              linux · networking · cloud · infrastructure
            </div>

            <div class="tech-line">
              <span class="prompt">$</span>
              examlab --status
            </div>

            <div class="tech-output status-online">
              ● platform operational
            </div>

          </div>

        </div>

      </section>


      <!-- CTA -->
      <section class="about-cta">

        <div>

          <div class="about-eyebrow">
            READY?
          </div>

          <h2>
            Start practicing.
          </h2>

          <p>
            Choose a certification and start your next practice exam.
          </p>

        </div>

        <RouterLink to="/" class="primary-link">
          View exams →
        </RouterLink>

      </section>

    </main>


    <!-- FOOTER -->
    <footer class="main-footer">
      ExamLab · Certification Practice Platform · 2026
    </footer>

  </div>
</template>