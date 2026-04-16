import { useState, useEffect } from "react"
import { authApi, type UserProfile } from "../api/endpoints"

export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    authApi.me()
      .then(r => setProfile(r.data))
      .catch(() => setError("Failed to load profile"))
      .finally(() => setLoading(false))
  }, [])

  return { profile, loading, error }
}
