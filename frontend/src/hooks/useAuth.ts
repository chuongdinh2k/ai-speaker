import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { authApi } from "../api/endpoints"

export function useAuth() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const login = async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      const resp = await authApi.login(email, password)
      localStorage.setItem("token", resp.data.access_token)
      navigate("/topics")
    } catch {
      setError("Invalid email or password")
    } finally {
      setLoading(false)
    }
  }

  const register = async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      await authApi.register(email, password)
      await login(email, password)
    } catch {
      setError("Registration failed. Email may already be in use.")
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem("token")
    navigate("/login")
  }

  return { login, register, logout, error, loading }
}
