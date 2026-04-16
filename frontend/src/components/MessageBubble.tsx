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
  const [textHidden, setTextHidden] = useState(!isUser)

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-1`}>
      <div className={`w-full max-w-[85%] sm:max-w-md px-4 py-2 rounded-2xl ${
        isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800 shadow-sm"
      }`}>
        {!isUser && (
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Script</span>
            <button
              onClick={() => setTextHidden(h => !h)}
              className="text-gray-400 hover:text-gray-600 shrink-0"
              title={textHidden ? "Show script" : "Hide script"}
            >
              {textHidden ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              )}
            </button>
          </div>
        )}
        {!textHidden && (
          <p className="text-sm leading-relaxed">
            {isUser ? message.content : highlightVocab(message.content, activeVocab)}
          </p>
        )}
        {message.audio_url && (
          <div className="mt-2">
            <audio controls src={message.audio_url} className="w-full h-8" />
          </div>
        )}
      </div>
    </div>
  )
}
