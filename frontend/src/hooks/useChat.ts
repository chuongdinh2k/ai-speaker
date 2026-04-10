import { useEffect, useRef, useState, useCallback } from "react"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("token")
    const wsUrl = `${import.meta.env.VITE_WS_URL ?? "ws://localhost:8000"}/ws/chat/${conversationId}?token=${token}`
    ws.current = new WebSocket(wsUrl)

    ws.current.onopen = () => setConnected(true)
    ws.current.onclose = () => setConnected(false)
    ws.current.onerror = () => setError("Connection error")
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "message") {
        setMessages(prev => [...prev, { role: "assistant", content: data.content, audio_url: data.audio_url }])
      } else if (data.type === "error") {
        setError(data.message)
      }
    }

    return () => ws.current?.close()
  }, [conversationId])

  const sendText = useCallback((content: string, replyWithVoice: boolean) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return
    setMessages(prev => [...prev, { role: "user", content }])
    ws.current.send(JSON.stringify({ type: "text", content, reply_with_voice: replyWithVoice }))
  }, [])

  const sendVoice = useCallback((audioBase64: string, replyWithVoice: boolean) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return
    ws.current.send(JSON.stringify({ type: "voice", audio_base64: audioBase64, reply_with_voice: replyWithVoice }))
  }, [])

  return { messages, connected, error, sendText, sendVoice }
}
