import { useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, loading, error, sendText, sendVoice, activeVocab } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
      </div>
      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2">{error}</div>}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((m, i) => <MessageBubble key={i} message={m} activeVocab={m.role === "assistant" ? activeVocab : []} />)}
        {loading && (
          <div className="flex justify-start mb-2">
            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-500 flex items-center gap-1 shadow-sm">
              <span className="animate-bounce [animation-delay:0ms]">●</span>
              <span className="animate-bounce [animation-delay:150ms]">●</span>
              <span className="animate-bounce [animation-delay:300ms]">●</span>
              <span className="ml-2">AI is thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <MessageInput onSendText={sendText} onSendVoice={sendVoice} disabled={loading} />
    </div>
  )
}
