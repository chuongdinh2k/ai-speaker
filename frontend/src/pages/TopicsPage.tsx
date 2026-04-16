import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { topicsApi, conversationsApi } from "../api/endpoints"
import type { Topic, Conversation } from "../api/endpoints"
import ConversationList from "../components/ConversationList"
import { useAuth } from "../hooks/useAuth"

function getInitials(email: string): string {
  return email.split("@")[0].slice(0, 2).toUpperCase()
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const { logout } = useAuth()
  const navigate = useNavigate()
  const email = (() => {
    try {
      const token = localStorage.getItem("token")
      if (!token) return ""
      const payload = JSON.parse(atob(token.split(".")[1]))
      return payload.email ?? ""
    } catch { return "" }
  })()

  useEffect(() => {
    topicsApi.list().then(r => setTopics(r.data))
    conversationsApi.list().then(r => setConversations(r.data))
  }, [])

  const startChat = async (topicId: string) => {
    const resp = await conversationsApi.create(topicId)
    navigate(`/chat/${resp.data.id}`)
  }

  const deleteConversation = async (id: string) => {
    await conversationsApi.delete(id)
    setConversations(prev => prev.filter(c => c.id !== id))
  }

  const topicNames = Object.fromEntries(topics.map(t => [t.id, t.name]))

  return (
    <div className="min-h-dvh bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between max-w-2xl mx-auto">
        <h1 className="text-lg font-bold">Topics</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/vocabulary")}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Vocabulary
          </button>
          <button
            onClick={() => navigate("/profile")}
            className="w-8 h-8 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center hover:opacity-80"
            title={email}
          >
            {email ? getInitials(email) : "?"}
          </button>
          <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-8">
        {/* Topics grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {topics.map(t => (
            <div key={t.id} className="bg-white border rounded-xl p-4 space-y-2 hover:shadow-md transition active:scale-95">
              <button onClick={() => startChat(t.id)} className="w-full text-left">
                <h2 className="font-semibold">{t.name}</h2>
                {t.description && <p className="text-gray-500 text-sm mt-1">{t.description}</p>}
              </button>
              <button
                onClick={() => navigate(`/topics/${t.id}/vocabulary`)}
                className="text-xs text-blue-500 hover:underline"
              >
                Vocabulary →
              </button>
            </div>
          ))}
        </div>

        {/* Conversations */}
        <div>
          <h2 className="text-base font-semibold mb-3">Your Conversations</h2>
          <ConversationList
            conversations={conversations}
            topicNames={topicNames}
            onDelete={deleteConversation}
            onOpen={id => navigate(`/chat/${id}`)}
          />
        </div>
      </div>
    </div>
  )
}
