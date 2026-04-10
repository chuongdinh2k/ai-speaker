import type { Conversation } from "../api/endpoints"

interface Props {
  conversations: Conversation[]
  topicNames: Record<string, string>
  onDelete: (id: string) => void
  onOpen: (id: string) => void
}

export default function ConversationList({ conversations, topicNames, onDelete, onOpen }: Props) {
  if (conversations.length === 0) return <p className="text-gray-400 text-sm">No conversations yet.</p>
  return (
    <ul className="space-y-2">
      {conversations.map(c => (
        <li key={c.id} className="flex items-center justify-between bg-white border rounded px-4 py-2">
          <button onClick={() => onOpen(c.id)} className="text-blue-600 hover:underline text-sm">
            {topicNames[c.topic_id] ?? "Unknown topic"}
          </button>
          <button onClick={() => onDelete(c.id)} className="text-red-400 hover:text-red-600 text-xs">
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
