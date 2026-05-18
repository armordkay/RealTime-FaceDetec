import { useSyncExternalStore } from 'react'

const STORAGE_KEY = 'face_attendance_auth'

let state = {
  token: null,
  user: null,
}

try {
  const persisted = localStorage.getItem(STORAGE_KEY)
  if (persisted) {
    const parsed = JSON.parse(persisted)
    state = {
      token: parsed.token || null,
      user: parsed.user || null,
    }
  }
} catch {
  state = { token: null, user: null }
}

const listeners = new Set()

function emit() {
  for (const listener of listeners) {
    listener()
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function subscribeAuthStore(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getAuthSnapshot() {
  return state
}

export function setAuthSession(token, user) {
  state = { token, user }
  persist()
  emit()
}

export function clearAuthSession() {
  state = { token: null, user: null }
  localStorage.removeItem(STORAGE_KEY)
  emit()
}

export function getAccessToken() {
  return state.token
}

export function useAuthStore() {
  return useSyncExternalStore(subscribeAuthStore, getAuthSnapshot, getAuthSnapshot)
}
