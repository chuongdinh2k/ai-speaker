import client from "./client"

export interface Topic {
  id: string
  name: string
  description: string | null
  system_prompt: string | null
}

export interface Conversation {
  id: string
  topic_id: string
  created_at: string
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    client.post<{ access_token: string }>("/auth/login", { email, password }),
  logout: () => client.post("/auth/logout"),
}

export const topicsApi = {
  list: () => client.get<Topic[]>("/topics"),
}

export const conversationsApi = {
  list: () => client.get<Conversation[]>("/conversations"),
  create: (topic_id: string) => client.post<Conversation>("/conversations", { topic_id }),
  delete: (id: string) => client.delete(`/conversations/${id}`),
}

export interface ChatSendResponse {
  user_message: { id: string; content: string }
  assistant_message: { id: string; content: string; audio_url: string | null }
}

export const chatApi = {
  send: (conversation_id: string, content: string, reply_with_voice: boolean) =>
    client.post<ChatSendResponse>("/chat/send", { conversation_id, content, reply_with_voice }),

  transcribe: (audioBlob: Blob) => {
    const form = new FormData()
    form.append("file", audioBlob, "audio.webm")
    return client.post<{ text: string }>("/voice/transcribe", form)
  },
}
