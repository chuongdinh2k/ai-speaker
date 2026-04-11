import { useState, useRef } from "react"

interface Props {
  onSendText: (text: string, replyWithVoice: boolean) => void
  onSendVoice: (blob: Blob, replyWithVoice: boolean) => void
  disabled: boolean
}

export default function MessageInput({ onSendText, onSendVoice, disabled }: Props) {
  const [text, setText] = useState("")
  const [replyWithVoice, setReplyWithVoice] = useState(false)
  const [recording, setRecording] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const handleSend = () => {
    if (!text.trim()) return
    onSendText(text.trim(), replyWithVoice)
    setText("")
  }

  const startRecording = async () => {
    setMicError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRef.current = new MediaRecorder(stream)
      chunksRef.current = []
      mediaRef.current.ondataavailable = e => chunksRef.current.push(e.data)
      mediaRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        onSendVoice(blob, replyWithVoice)
        stream.getTracks().forEach(t => t.stop())
      }
      mediaRef.current.start()
      setRecording(true)
    } catch {
      setMicError("Microphone access denied. Please allow microphone access and try again.")
    }
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="flex flex-col border-t bg-white">
      {micError && <div className="text-red-500 text-xs px-4 pt-2">{micError}</div>}
    <div className="flex items-center gap-2 p-4">
      <input
        value={text} onChange={e => setText(e.target.value)}
        onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
        placeholder="Type a message..." disabled={disabled}
        className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <button onClick={handleSend} disabled={disabled || !text.trim()}
        className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
        Send
      </button>
      <button
        onMouseDown={startRecording} onMouseUp={stopRecording}
        disabled={disabled}
        className={`px-4 py-2 rounded text-sm ${recording ? "bg-red-500 text-white" : "bg-gray-200 text-gray-700"} hover:opacity-80 disabled:opacity-50`}>
        {recording ? "Recording..." : "Voice"}
      </button>
      <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
        <input type="checkbox" checked={replyWithVoice} onChange={e => setReplyWithVoice(e.target.checked)} />
        Voice reply
      </label>
    </div>
    </div>
  )
}
