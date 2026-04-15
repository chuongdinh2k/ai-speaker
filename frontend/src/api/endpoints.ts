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

export interface MessageOut {
  id: string
  role: "user" | "assistant"
  content: string
  audio_url: string | null
}

export interface ChatSendResponse {
  user_message: MessageOut
  assistant_message: MessageOut
  active_vocab: string[]
}

export interface ChatHistoryResponse {
  messages: MessageOut[]
  next_cursor: string | null
}

export const chatApi = {
  history: (conversation_id: string, cursor?: string) =>
    client.get<ChatHistoryResponse>(`/chat/${conversation_id}/messages`, {
      params: cursor ? { cursor } : undefined,
    }),

  sendText: (conversation_id: string, content: string, reply_with_voice: boolean) => {
    const form = new FormData()
    form.append("conversation_id", conversation_id)
    form.append("content", content)
    form.append("reply_with_voice", String(reply_with_voice))
    return client.post<ChatSendResponse>("/chat/send", form)
  },

  sendAudio: (conversation_id: string, audioBlob: Blob, reply_with_voice: boolean) => {
    const form = new FormData()
    form.append("conversation_id", conversation_id)
    form.append("audio", audioBlob, "audio.webm")
    form.append("reply_with_voice", String(reply_with_voice))
    return client.post<ChatSendResponse>("/chat/send", form)
  },
}

export interface VocabularyItem {
  id: string
  user_id: string
  topic_id: string
  word: string
  added_at: string
  usage_count: number
  is_active: boolean
}

export const vocabularyApi = {
  list: (topic_id: string) =>
    client.get<VocabularyItem[]>("/vocabularies", { params: { topic_id } }),
  add: (topic_id: string, word: string) =>
    client.post<VocabularyItem>("/vocabularies", { topic_id, word }),
  delete: (id: string) => client.delete(`/vocabularies/${id}`),
  activate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/activate`),
  deactivate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/deactivate`),
}
