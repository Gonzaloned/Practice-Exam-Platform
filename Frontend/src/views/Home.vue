<script setup lang="ts">
import '../assets/styles/home.css'
</script>

<template>
  <div class="public-page">

    <header class="main-navbar">

      <div class="brand">
        <div class="brand-mark">E</div>

        <div>
          <div class="brand-name">ExamLab</div>
          <div class="brand-subtitle">
            Certification Practice
          </div>
        </div>
      </div>

      <nav>
        <RouterLink to="/">
          Exams
        </RouterLink>

        <RouterLink to="/about">
          About
        </RouterLink>

        <RouterLink to="/login" class="login-link">
          Sign in
        </RouterLink>
      </nav>

    </header>


    <main>

      <!-- HERO -->

      <section class="home-hero">

        <div class="home-hero-content">

          <div class="home-eyebrow">
            CERTIFICATION PRACTICE PLATFORM
          </div>

          <h1>
            Prepare for your
            next IT certification.
          </h1>

          <p>
            Practice with realistic certification exams
            designed to help you test your knowledge,
            identify weak areas, and build confidence
            before the real exam.
          </p>

          <RouterLink to="/login" class="primary-link">
            Browse exams
          </RouterLink>

        </div>

      </section>


      <!-- EXAMS -->

      <section class="exams-section">

        <div class="section-heading">

          <div class="eyebrow">
            AVAILABLE EXAMS
          </div>

          <h2>
            Certification practice
          </h2>

        </div>


        <div class="exam-grid">

          <article class="public-exam-card">

            <div class="exam-icon">
              LF
            </div>

            <h3>
              Linux Foundation
            </h3>

            <p>
              Practice Linux administration and
              prepare for Linux Foundation certifications.
            </p>

            <RouterLink to="/login">
              View exam →
            </RouterLink>

          </article>


          <article class="public-exam-card">

            <div class="exam-icon">
              CC
            </div>

            <h3>
              Cisco
            </h3>

            <p>
              Practice networking concepts and prepare
              for Cisco certification exams.
            </p>

            <RouterLink to="/login">
              View exam →
            </RouterLink>

          </article>


          <article class="public-exam-card">

            <div class="exam-icon">
              AZ
            </div>

            <h3>
              Microsoft Azure
            </h3>

            <p>
              Test your knowledge of Azure services,
              infrastructure, and cloud concepts.
            </p>

            <RouterLink to="/login">
              View exam →
            </RouterLink>

          </article>

        </div>

      </section>


      <!-- FEATURES -->

      <section class="home-features">

        <div class="section-heading">

          <div class="eyebrow">
            BUILT FOR PRACTICE
          </div>

          <h2>
            Focus on what matters.
          </h2>

        </div>


        <div class="home-feature-grid">

          <article class="home-feature">

            <div class="feature-number">
              01
            </div>

            <h3>
              Realistic environments
            </h3>

            <p>
              Practice in an environment designed
              to feel closer to a real certification exam.
            </p>

          </article>


          <article class="home-feature">

            <div class="feature-number">
              02
            </div>

            <h3>
              Track your progress
            </h3>

            <p>
              Review completed tasks and identify
              the areas where you need more practice.
            </p>

          </article>


          <article class="home-feature">

            <div class="feature-number">
              03
            </div>

            <h3>
              Practice with confidence
            </h3>

            <p>
              Repeat exams and strengthen your knowledge
              before taking the official certification.
            </p>

          </article>

        </div>

      </section>

    </main>


    <footer class="main-footer">
      ExamLab · Certification Practice Platform · 2026
    </footer>

  </div>
</template>
