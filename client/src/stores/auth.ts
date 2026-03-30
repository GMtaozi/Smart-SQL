import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, register, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<{ id: number; username: string; email?: string } | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function loginAction(username: string, password: string) {
    const response = await login(username, password)
    token.value = response.access_token
    localStorage.setItem('token', response.access_token)
    user.value = {
      id: response.user_id,
      username: response.username,
    }
    return response
  }

  async function registerAction(username: string, password: string, email?: string) {
    return await register(username, password, email)
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    try {
      const response = await getCurrentUser()
      user.value = {
        id: response.id,
        username: response.username,
        email: response.email,
      }
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    loginAction,
    registerAction,
    fetchCurrentUser,
    logout,
  }
})
