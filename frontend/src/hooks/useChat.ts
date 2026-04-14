import { useState, useCallback, useEffect } from "react"
import { chatApi } from "../api/endpoints"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load history on mount
  useEffect(() => {
    let cancelled = false
    async function loadHistory() {
      try {
        const res = await chatApi.history(conversationId)
        if (!cancelled) {
          setMessages(res.data.messages.map(m => ({
            role: m.role,
            content: m.content,
            audio_url: m.audio_url,
          })))
        }
      } catch {
        // Silently ignore — empty chat is fine
      }
    }
    loadHistory()
    return () => { cancelled = true }
  }, [conversationId])

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.sendText(conversationId, content, replyWithVoice)
      const { user_message, assistant_message } = res.data
      // Replace the optimistic user message with the real one (includes audio_url)
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  const sendVoice = useCallback(async (audioBlob: Blob, replyWithVoice: boolean) => {
    setError(null)
    setLoading(true)
    try {
      const res = await chatApi.sendAudio(conversationId, audioBlob, replyWithVoice)
      const { user_message, assistant_message } = res.data
      setMessages(prev => [
        ...prev,
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  return { messages, loading, error, sendText, sendVoice }
}
