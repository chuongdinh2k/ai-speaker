import { useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, connected, error, sendText, sendVoice } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
        <span className={`text-xs ${connected ? "text-green-500" : "text-red-400"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2">{error}</div>}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((m, i) => <MessageBubble key={i} message={m} />)}
        <div ref={bottomRef} />
      </div>
      <MessageInput onSendText={sendText} onSendVoice={sendVoice} disabled={!connected} />
    </div>
  )
}
