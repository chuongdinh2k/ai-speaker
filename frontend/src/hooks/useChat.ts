import { useState, useCallback, useEffect, useRef } from "react"
import { chatApi, conversationsApi } from "../api/endpoints"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeVocab, setActiveVocab] = useState<string[]>([])
  const [topicName, setTopicName] = useState<string>("")
  const lastAudioUrlRef = useRef<string | null>(null)

  // Load history and topic name on mount
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

    async function loadTopicName() {
      try {
        const res = await conversationsApi.list()
        const conv = res.data.find(c => c.id === conversationId)
        if (conv && !cancelled) setTopicName(conv.topic_name)
      } catch {
        // Not critical
      }
    }

    loadHistory()
    loadTopicName()
    return () => { cancelled = true }
  }, [conversationId])

  // Auto-play latest assistant audio
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (
      last &&
      last.role === "assistant" &&
      last.audio_url &&
      last.audio_url !== lastAudioUrlRef.current
    ) {
      lastAudioUrlRef.current = last.audio_url
      const audio = new Audio(last.audio_url)
      audio.play().catch(() => {
        // Auto-play blocked by browser — user will need to tap play manually
      })
    }
  }, [messages])

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.sendText(conversationId, content, replyWithVoice)
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
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
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
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

  return { messages, loading, error, sendText, sendVoice, activeVocab, topicName }
}
