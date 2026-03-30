import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/chat',
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
      },
      {
        path: 'datasource',
        name: 'Datasource',
        component: () => import('@/views/Datasource.vue'),
      },
      {
        path: 'ai-model',
        name: 'AIModel',
        component: () => import('@/views/AIModel.vue'),
      },
      {
        path: 'terminology',
        name: 'Terminology',
        component: () => import('@/views/Terminology.vue'),
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/Training.vue'),
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/History.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  // Check for token in localStorage directly for initial auth state
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth === false) {
    // Public route
    if (to.path === '/login' && token) {
      next('/chat')
    } else {
      next()
    }
  } else {
    // Protected route
    if (!token) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router
