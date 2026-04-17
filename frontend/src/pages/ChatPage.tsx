import { useEffect, useRef, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"
import { conversationsApi, type ConversationContext } from "../api/endpoints"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, loading, error, sendText, sendVoice, activeVocab, topicName } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const [showModal, setShowModal] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<ConversationContext>({
    name: "",
    occupation: "",
    learning_goal: "",
    preferred_tone: "casual",
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  function showToast(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  async function handleSaveContext(e: React.FormEvent) {
    e.preventDefault()
    if (!conversationId) return
    setSaving(true)
    try {
      const resp = await conversationsApi.updateContext(conversationId, form)
      if (resp.data.user_context) {
        setForm(resp.data.user_context)
      }
      setShowModal(false)
      showToast("Context saved. It will apply when you re-enter this conversation.")
    } catch {
      showToast("Failed to save context. Please try again.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col h-dvh bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white border-b shrink-0">
        <button
          onClick={() => navigate("/topics")}
          className="text-blue-600 text-sm hover:underline shrink-0"
        >
          ←
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold truncate">{topicName || "Chat"}</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="text-xs text-blue-600 border border-blue-200 rounded px-2 py-1 hover:bg-blue-50 shrink-0"
        >
          Update Context
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2 shrink-0">{error}</div>}

      {/* Toast */}
      {toast && (
        <div className="bg-green-50 text-green-700 text-sm px-4 py-2 shrink-0 border-b border-green-100">
          {toast}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-2 py-4">
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            message={m}
            activeVocab={m.role === "assistant" ? activeVocab : []}
          />
        ))}
        {loading && (
          <div className="flex justify-start mb-2 px-1">
            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-500 flex items-center gap-1 shadow-sm">
              <span className="animate-bounce [animation-delay:0ms]">●</span>
              <span className="animate-bounce [animation-delay:150ms]">●</span>
              <span className="animate-bounce [animation-delay:300ms]">●</span>
              <span className="ml-2 text-xs">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <MessageInput onSendText={sendText} onSendVoice={sendVoice} disabled={loading} />

      {/* Context Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-6">
            <h2 className="text-base font-semibold mb-4">Update Conversation Context</h2>
            <form onSubmit={handleSaveContext} className="flex flex-col gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Name</label>
                <input
                  type="text"
                  placeholder="e.g. Alex"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Occupation</label>
                <input
                  type="text"
                  placeholder="e.g. Software engineer, student, teacher..."
                  value={form.occupation}
                  onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Learning goal</label>
                <input
                  type="text"
                  placeholder="e.g. Job interviews, travel, daily conversation..."
                  value={form.learning_goal}
                  onChange={e => setForm(f => ({ ...f, learning_goal: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Preferred tone</label>
                <select
                  value={form.preferred_tone}
                  onChange={e => setForm(f => ({ ...f, preferred_tone: e.target.value as ConversationContext["preferred_tone"] }))}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                  <option value="friendly">Friendly</option>
                </select>
              </div>
              <div className="flex gap-2 justify-end mt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="text-sm px-4 py-2 rounded-lg border hover:bg-gray-50"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
