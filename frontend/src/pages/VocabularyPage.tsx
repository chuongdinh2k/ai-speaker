import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { vocabularyApi } from "../api/endpoints"
import type { VocabularyItem } from "../api/endpoints"

export default function VocabularyPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const navigate = useNavigate()
  const [words, setWords] = useState<VocabularyItem[]>([])
  const [newWord, setNewWord] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (topicId) {
      vocabularyApi.list(topicId).then(r => setWords(r.data))
    }
  }, [topicId])

  const handleAdd = async () => {
    const trimmed = newWord.trim()
    if (!trimmed || !topicId) return
    setError(null)
    try {
      const res = await vocabularyApi.add(topicId, trimmed)
      setWords(prev => [res.data, ...prev])
      setNewWord("")
    } catch {
      setError("Failed to add word.")
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await vocabularyApi.delete(id)
      setWords(prev => prev.filter(w => w.id !== id))
    } catch {
      setError("Failed to delete word.")
    }
  }

  const handleToggleActive = async (item: VocabularyItem) => {
    setError(null)
    try {
      const res = item.is_active
        ? await vocabularyApi.deactivate(item.id)
        : await vocabularyApi.activate(item.id)
      setWords(prev => prev.map(w => w.id === item.id ? res.data : w))
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to update word."
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back to Topics
        </button>
        <h1 className="text-2xl font-bold">My Vocabulary</h1>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={newWord}
          onChange={e => setNewWord(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleAdd()}
          placeholder="Add a new word..."
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          onClick={handleAdd}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
        >
          Add
        </button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <table className="w-full bg-white border rounded-lg text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="px-4 py-2">Word</th>
            <th className="px-4 py-2">Added</th>
            <th className="px-4 py-2">Times Used</th>
            <th className="px-4 py-2">Active</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {words.map(item => (
            <tr key={item.id} className="border-b last:border-0">
              <td className="px-4 py-2 font-medium">{item.word}</td>
              <td className="px-4 py-2 text-gray-500">{new Date(item.added_at).toLocaleDateString()}</td>
              <td className="px-4 py-2 text-gray-500">{item.usage_count}</td>
              <td className="px-4 py-2">
                <button
                  onClick={() => handleToggleActive(item)}
                  className={`px-2 py-1 rounded text-xs ${item.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                >
                  {item.is_active ? "Active" : "Inactive"}
                </button>
              </td>
              <td className="px-4 py-2">
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-red-400 hover:text-red-600 text-xs"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {words.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-gray-400">No words yet. Add your first word above.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
