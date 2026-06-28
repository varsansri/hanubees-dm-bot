import { useState } from 'react'

export function useAuth() {
  const [token] = useState(() => localStorage.getItem('token'))
  return { isLoggedIn: !!token, token }
}

export function logout() {
  localStorage.removeItem('token')
  window.location.href = '/login'
}
