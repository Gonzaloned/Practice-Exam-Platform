import { createRouter, createWebHistory } from 'vue-router'

import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import About from '../views/About.vue'
import Exam from '../views/Exam.vue'
import Register from '../views/Register.vue'
const router = createRouter({
  history: createWebHistory(),

  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
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
      name: 'Exam',
      component: Exam,
    },
        {
      path: '/register',
      name: 'register',
      component: Register,
    }
  ],
})

export default router