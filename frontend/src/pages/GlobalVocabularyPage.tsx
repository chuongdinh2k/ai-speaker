import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { vocabularyApi, type VocabularyItemWithTopic } from "../api/endpoints"

export default function GlobalVocabularyPage() {
  const navigate = useNavigate()
  const [words, setWords] = useState<VocabularyItemWithTopic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vocabularyApi.listAll()
      .then(r => setWords(r.data))
      .catch(() => setError("Failed to load vocabulary"))
      .finally(() => setLoading(false))
  }, [])

  // Group by topic_name
  const grouped = words.reduce<Record<string, VocabularyItemWithTopic[]>>((acc, item) => {
    if (!acc[item.topic_name]) acc[item.topic_name] = []
    acc[item.topic_name].push(item)
    return acc
  }, {})

  return (
    <div className="min-h-dvh bg-gray-50 px-4 py-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
        <h1 className="text-xl font-bold">My Vocabulary</h1>
        <span className="ml-auto text-sm text-gray-400">{words.length} words</span>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {!loading && words.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-16">No vocabulary yet. Add words from a topic page.</p>
      )}

      <div className="space-y-6">
        {Object.entries(grouped).map(([topicName, items]) => (
          <div key={topicName}>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">
              {topicName}
            </h2>
            <div className="space-y-2">
              {items.map(item => (
                <div
                  key={item.id}
                  className="bg-white border rounded-xl px-4 py-3 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.word}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Added {new Date(item.added_at).toLocaleDateString()} · Used {item.usage_count}×
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    item.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-400"
                  }`}>
                    {item.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
