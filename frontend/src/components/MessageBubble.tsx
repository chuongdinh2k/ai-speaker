import { useState } from "react"
import type { ChatMessage } from "../hooks/useChat"

function highlightVocab(content: string, activeVocab: string[]): React.ReactNode {
  if (!activeVocab.length) return content

  const pattern = new RegExp(
    `(${activeVocab.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})`,
    "gi"
  )
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
  const [textHidden, setTextHidden] = useState(false)

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-1`}>
      <div className={`max-w-[85%] sm:max-w-md px-4 py-2 rounded-2xl ${
        isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800 shadow-sm"
      }`}>
        {!textHidden && (
          <p className="text-sm leading-relaxed">
            {isUser ? message.content : highlightVocab(message.content, activeVocab)}
          </p>
        )}
        {message.audio_url && (
          <div className="mt-2 flex items-center gap-2">
            <audio controls src={message.audio_url} className="w-full h-8" />
            {!isUser && (
              <button
                onClick={() => setTextHidden(h => !h)}
                className="text-gray-400 hover:text-gray-600 text-xs shrink-0"
                title={textHidden ? "Show text" : "Hide text"}
              >
                {textHidden ? "👁" : "🙈"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
