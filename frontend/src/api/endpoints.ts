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
  topic_name: string
  created_at: string
  message_count: number
}

export interface UserProfile {
  id: string
  email: string
  role: string
  level: string
  avatar_url: string | null
  total_messages: number
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    client.post<{ access_token: string }>("/auth/login", { email, password }),
  logout: () => client.post("/auth/logout"),
  me: () => client.get<UserProfile>("/auth/me"),
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

export interface VocabularyItemWithTopic extends VocabularyItem {
  topic_name: string
}

export const vocabularyApi = {
  list: (topic_id: string) =>
    client.get<VocabularyItem[]>("/vocabularies", { params: { topic_id } }),
  listAll: () =>
    client.get<VocabularyItemWithTopic[]>("/vocabularies/all"),
  add: (topic_id: string, word: string) =>
    client.post<VocabularyItem>("/vocabularies", { topic_id, word }),
  delete: (id: string) => client.delete(`/vocabularies/${id}`),
  activate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/activate`),
  deactivate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/deactivate`),
}

export interface AdminUser {
  id: string
  email: string
  role: string
  level: string
  created_at: string
}

export interface AdminTopic {
  id: string
  name: string
  description: string | null
  system_prompt: string | null
  created_at: string
}

export const adminApi = {
  // Users
  listUsers: () => client.get<AdminUser[]>("/admin/users"),
  updatePassword: (id: string, password: string) =>
    client.patch(`/admin/users/${id}/password`, { password }),
  deleteUser: (id: string) => client.delete(`/admin/users/${id}`),

  // Topics
  listTopics: () => client.get<AdminTopic[]>("/admin/topics"),
  createTopic: (name: string, description?: string, system_prompt?: string) =>
    client.post<AdminTopic>("/admin/topics", { name, description, system_prompt }),
  updateTopic: (id: string, description?: string, system_prompt?: string) =>
    client.patch<AdminTopic>(`/admin/topics/${id}`, { description, system_prompt }),
  deleteTopic: (id: string) => client.delete(`/admin/topics/${id}`),
}
