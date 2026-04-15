import type { ChatMessage } from "../hooks/useChat"

function highlightVocab(content: string, activeVocab: string[]): React.ReactNode {
  if (!activeVocab.length) return content

  const pattern = new RegExp(`(${activeVocab.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})`, "gi")
  const parts = content.split(pattern)

  return parts.map((part, i) => {
    const isMatch = activeVocab.some(w => w.toLowerCase() === part.toLowerCase())
    return isMatch
      ? <mark key={i} className="bg-yellow-200 rounded px-0.5">{part}</mark>
      : part
  })
}

export default function MessageBubble({
  message,
  activeVocab = [],
}: {
  message: ChatMessage
  activeVocab?: string[]
}) {
  const isUser = message.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800"}`}>
        <p className="text-sm">
          {isUser ? message.content : highlightVocab(message.content, activeVocab)}
        </p>
        {message.audio_url && (
          <audio controls src={message.audio_url} className="mt-2 w-full" />
        )}
      </div>
    </div>
  )
}
