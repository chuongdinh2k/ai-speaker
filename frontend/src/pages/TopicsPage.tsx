import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { topicsApi, conversationsApi } from "../api/endpoints"
import type { Topic, Conversation } from "../api/endpoints"
import ConversationList from "../components/ConversationList"
import { useAuth } from "../hooks/useAuth"

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const { logout } = useAuth()
  const navigate = useNavigate()

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
    <div className="min-h-screen bg-gray-50 p-8 max-w-2xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Topics</h1>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">Logout</button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {topics.map(t => (
          <div key={t.id} className="bg-white border rounded-lg p-4 space-y-2 hover:shadow-md transition">
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
      <div>
        <h2 className="text-lg font-semibold mb-3">Your Conversations</h2>
        <ConversationList
          conversations={conversations}
          topicNames={topicNames}
          onDelete={deleteConversation}
          onOpen={id => navigate(`/chat/${id}`)}
        />
      </div>
    </div>
  )
}
