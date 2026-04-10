import type { ChatMessage } from "../hooks/useChat"

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800"}`}>
        <p className="text-sm">{message.content}</p>
        {message.audio_url && (
          <audio controls src={message.audio_url} className="mt-2 w-full" />
        )}
      </div>
    </div>
  )
}
