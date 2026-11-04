import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from './store'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuth = useAuthStore((s) => s.isAuthenticated)
  const location = useLocation()
  if (!isAuth) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}

export function PublicRoute({ children }: { children: ReactNode }) {
  const isAuth = useAuthStore((s) => s.isAuthenticated)
  if (isAuth) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}
