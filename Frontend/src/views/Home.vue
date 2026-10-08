<script setup lang="ts">
import AppNavBar from '../components/AppNavBar.vue'
import { catalogExams } from '../data/catalog'
import '../assets/styles/home.css'

const availableTaskCount = catalogExams.reduce(
  (total, exam) => total + exam.taskCount,
  0
)
</script>

<template>
  <div class="public-page home-page">
    <AppNavBar />

    <main>
      <section class="home-hero">
        <div class="home-hero-copy">
          <div class="home-eyebrow">
            <span class="home-eyebrow-dot"></span>
            HANDS-ON CERTIFICATION PRACTICE
          </div>
          <h1>
            Build the confidence to
            <span>pass your next exam.</span>
          </h1>
          <p>
            Move beyond flashcards. Practice the real skills behind IT
            certifications in focused, task-based exam environments.
          </p>
          <div class="home-hero-actions">
            <RouterLink to="/exams" class="home-primary-link">
              Explore practice exams
              <span aria-hidden="true">→</span>
            </RouterLink>
            <RouterLink to="/about" class="home-secondary-link">
              Discover ExamLab
            </RouterLink>
          </div>
          <div class="home-hero-note">
            <span aria-hidden="true">✓</span>
            Learn by doing, at your own pace.
          </div>
        </div>

        <div class="home-preview" aria-label="Example exam task preview">
          <div class="home-preview-toolbar">
            <div class="home-preview-brand">
              <span class="home-preview-mark">E</span>
              <span>EXAMLAB <span class="home-preview-divider">/</span> PRACTICE</span>
            </div>
            <span class="home-preview-live">
              <span></span>
              SESSION READY
            </span>
          </div>

          <div class="home-preview-body">
            <div class="home-preview-sidebar">
              <div class="home-preview-sidebar-label">TASKS</div>
              <div class="home-preview-task is-complete">
                <span>01</span>
                User management
                <b>✓</b>
              </div>
              <div class="home-preview-task is-complete">
                <span>02</span>
                File permissions
                <b>✓</b>
              </div>
              <div class="home-preview-task is-current">
                <span>03</span>
                Network config
                <i></i>
              </div>
              <div class="home-preview-task">
                <span>04</span>
                Storage
              </div>
            </div>

            <div class="home-preview-content">
              <div class="home-preview-kicker">NETWORKING / TASK 03</div>
              <h2>Configure a static IP address</h2>
              <p>
                Set a persistent IPv4 address for the primary network interface.
              </p>
              <div class="home-terminal">
                <div><span>$</span> ip addr show</div>
                <div class="home-terminal-muted">2: enp1s0: &lt;BROADCAST,MULTICAST,UP&gt;</div>
                <div><span>$</span> _</div>
              </div>
              <div class="home-preview-progress">
                <span>YOUR PROGRESS</span>
                <strong>2 <small>/ {{ availableTaskCount }}</small></strong>
                <div><i></i></div>
              </div>
            </div>
          </div>
          <div class="home-preview-footer">
            <span>REALISTIC TASKS</span>
            <span>·</span>
            <span>STRUCTURED PRACTICE</span>
            <span>·</span>
            <span>YOUR PACE</span>
          </div>
        </div>
      </section>

      <section class="home-proof-strip" aria-label="ExamLab practice format">
        <div>
          <strong>{{ catalogExams.length }}</strong>
          <span>{{ catalogExams.length === 1 ? 'available practice exam' : 'available practice exams' }}</span>
        </div>
        <div>
          <strong>{{ availableTaskCount }}</strong>
          <span>hands-on tasks to explore</span>
        </div>
        <div>
          <strong>Practical</strong>
          <span>skills, not just memorization</span>
        </div>
      </section>

      <section class="home-benefits">
        <div class="home-section-heading">
          <div class="home-eyebrow">A BETTER WAY TO PREPARE</div>
          <h2>Turn what you know into what you can do.</h2>
          <p>
            Certification is about applying knowledge under pressure.
            ExamLab gives you space to practice that experience.
          </p>
        </div>

        <div class="home-benefit-grid">
          <article class="home-benefit-card">
            <div class="home-benefit-number">01</div>
            <div class="home-benefit-symbol" aria-hidden="true">⌘</div>
            <h3>Practice real tasks</h3>
            <p>
              Work through practical challenges that reflect the tools and
              decisions you need to make on the job.
            </p>
          </article>
          <article class="home-benefit-card">
            <div class="home-benefit-number">02</div>
            <div class="home-benefit-symbol" aria-hidden="true">◷</div>
            <h3>Find your weak spots</h3>
            <p>
              See which topics need another look and use your practice time
              where it can make the most difference.
            </p>
          </article>
          <article class="home-benefit-card">
            <div class="home-benefit-number">03</div>
            <div class="home-benefit-symbol" aria-hidden="true">↗</div>
            <h3>Build exam confidence</h3>
            <p>
              Get comfortable navigating hands-on challenges before exam day,
              one focused session at a time.
            </p>
          </article>
        </div>
      </section>

      <section class="home-how">
        <div class="home-how-copy">
          <div class="home-eyebrow">YOUR NEXT STEP STARTS HERE</div>
          <h2>Simple to start.<br />Meaningful to practice.</h2>
          <p>
            Pick a certification, review what it covers, then jump into a
            practical exam session. Keep practicing until the steps feel
            natural.
          </p>
          <RouterLink to="/exams" class="home-text-link">
            Find your practice exam <span aria-hidden="true">→</span>
          </RouterLink>
        </div>

        <ol class="home-steps">
          <li>
            <span>01</span>
            <div>
              <strong>Choose an exam</strong>
              <p>Explore the catalog and see the skills each exam covers.</p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>Take on the tasks</strong>
              <p>Use the exam workspace to work through each challenge.</p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <strong>Keep getting better</strong>
              <p>Review, repeat, and build confidence through practice.</p>
            </div>
          </li>
        </ol>
      </section>

      <section class="home-final-cta">
        <div>
          <div class="home-eyebrow">READY WHEN YOU ARE</div>
          <h2>Your next certification starts with practice.</h2>
          <p>Explore available exams and take the first step today.</p>
        </div>
        <RouterLink to="/exams" class="home-primary-link">
          Browse exams
          <span aria-hidden="true">→</span>
        </RouterLink>
      </section>
    </main>

    <footer class="main-footer">
      ExamLab · Certification Practice Platform · 2026
    </footer>
  </div>
</template>
