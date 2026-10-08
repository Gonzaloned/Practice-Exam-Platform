import { createRouter, createWebHistory } from 'vue-router'

import Home from '../views/Home.vue'
import ExamCatalog from '../views/ExamCatalog.vue'
import Login from '../views/Login.vue'
import About from '../views/About.vue'
import Exam from '../views/Exam.vue'
import ExamDetails from '../views/ExamDetails.vue'
import Register from '../views/Register.vue'
import AccountPage from '../views/AccountPage.vue'
import { hasAccessToken } from '../services/auth'

const router = createRouter({
  history: createWebHistory(),

  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
    },
    {
      path: '/exams',
      name: 'exam-catalog',
      component: ExamCatalog,
    },
    {
      path: '/exams/:slug',
      name: 'exam-details',
      component: ExamDetails,
    },
    {
      path: '/login',
      name: 'login',
      component: Login,
    },
    {
      path: '/about',
      name: 'nosotros',
      component: About,
    },
    {
      path: '/exam',
      redirect: '/exams',
    },
    {
      path: '/exam-session/:sessionId',
      name: 'exam-session',
      component: Exam,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/exam-results/:sessionId',
      name: 'exam-results',
      component: () => import('../views/ExamResults.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/register',
      name: 'register',
      component: Register,
    },
    {
      path: '/profile',
      name: 'profile',
      component: AccountPage,
      meta: {
        requiresAuth: true,
        title: 'My profile',
        description: 'Manage your ExamLab profile.',
        emptyMessage: 'Your profile details will be available here.',
      },
    },
    {
      path: '/my-exams',
      name: 'my-exams',
      component: AccountPage,
      meta: {
        requiresAuth: true,
        title: 'My exams',
        description: 'Review your certification practice.',
        emptyMessage: 'You have no exams in progress yet.',
      },
    },
    {
      path: '/settings',
      name: 'settings',
      component: AccountPage,
      meta: {
        requiresAuth: true,
        title: 'Settings',
        description: 'Manage your account preferences.',
        emptyMessage: 'Your account preferences will be available here.',
      },
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !hasAccessToken()) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
})

export default router