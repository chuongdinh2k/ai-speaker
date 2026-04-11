import { useState, useCallback } from "react"
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

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.send(conversationId, content, replyWithVoice)
      const { assistant_message } = res.data
      setMessages(prev => [...prev, {
        role: "assistant",
        content: assistant_message.content,
        audio_url: assistant_message.audio_url,
      }])
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
      const transcribeRes = await chatApi.transcribe(audioBlob)
      const transcribedText = transcribeRes.data.text
      setMessages(prev => [...prev, { role: "user", content: transcribedText }])
      try {
        const res = await chatApi.send(conversationId, transcribedText, replyWithVoice)
        const { assistant_message } = res.data
        setMessages(prev => [...prev, {
          role: "assistant",
          content: assistant_message.content,
          audio_url: assistant_message.audio_url,
        }])
      } catch {
        setError("Failed to get a response. Please try again.")
      }
    } catch {
      setError("Transcription failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  return { messages, loading, error, sendText, sendVoice }
}
