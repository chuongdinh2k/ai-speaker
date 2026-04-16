import { useNavigate } from "react-router-dom"
import { useProfile } from "../hooks/useProfile"

function getInitials(email: string): string {
  return email.split("@")[0].slice(0, 2).toUpperCase()
}

function getAvatarColor(email: string): string {
  const colors = [
    "bg-blue-500", "bg-purple-500", "bg-green-500",
    "bg-yellow-500", "bg-red-500", "bg-indigo-500",
    "bg-pink-500", "bg-teal-500",
  ]
  let hash = 0
  for (let i = 0; i < email.length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

const LEVEL_COLORS: Record<string, string> = {
  A1: "bg-gray-100 text-gray-600",
  A2: "bg-blue-100 text-blue-700",
  B1: "bg-green-100 text-green-700",
  B2: "bg-yellow-100 text-yellow-700",
  C1: "bg-orange-100 text-orange-700",
  C2: "bg-red-100 text-red-700",
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const { profile, loading, error } = useProfile()

  return (
    <div className="min-h-dvh bg-gray-50 px-4 py-6 max-w-lg mx-auto">
      <button
        onClick={() => navigate("/topics")}
        className="text-sm text-blue-600 hover:underline mb-6 inline-block"
      >
        ← Back
      </button>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {profile && (
        <div className="bg-white rounded-2xl shadow-sm border p-6 space-y-6">
          {/* Avatar */}
          <div className="flex flex-col items-center gap-3">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt="Avatar"
                className="w-20 h-20 rounded-full object-cover"
              />
            ) : (
              <div className={`w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-bold ${getAvatarColor(profile.email)}`}>
                {getInitials(profile.email)}
              </div>
            )}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${LEVEL_COLORS[profile.level] ?? "bg-gray-100 text-gray-600"}`}>
              {profile.level}
            </span>
          </div>

          {/* Details */}
          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Email</p>
              <p className="text-sm font-medium text-gray-800 break-all">{profile.email}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">CEFR Level</p>
              <p className="text-sm font-medium text-gray-800">{profile.level}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Messages Sent</p>
              <p className="text-2xl font-bold text-blue-600">{profile.total_messages}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Role</p>
              <p className="text-sm font-medium text-gray-800 capitalize">{profile.role}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
