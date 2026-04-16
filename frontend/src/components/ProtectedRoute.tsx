import { Navigate } from "react-router-dom"

interface Props {
  children: React.ReactNode
  requiredRole?: "admin" | "user"
}

function getTokenPayload(): { role?: string } | null {
  try {
    const token = localStorage.getItem("token")
    if (!token) return null
    return JSON.parse(atob(token.split(".")[1]))
  } catch {
    return null
  }
}

export default function ProtectedRoute({ children, requiredRole }: Props) {
  const payload = getTokenPayload()

  if (!payload) return <Navigate to="/login" replace />

  if (requiredRole && payload.role !== requiredRole) {
    return <Navigate to="/topics" replace />
  }

  return <>{children}</>
}
