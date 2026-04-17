import { useEffect, useState } from "react"
import { adminApi, type AdminTopic } from "../../api/endpoints"

type FormState = {
  name: string
  description: string
  system_prompt: string
}

const emptyForm: FormState = { name: "", description: "", system_prompt: "" }

export default function AdminTopicsPage() {
  const [topics, setTopics] = useState<AdminTopic[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState<FormState>(emptyForm)
  const [editId, setEditId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Pick<FormState, "description" | "system_prompt">>({ description: "", system_prompt: "" })

  useEffect(() => {
    adminApi.listTopics().then(r => setTopics(r.data))
  }, [])

  const handleCreate = async () => {
    if (!createForm.name.trim()) return
    const r = await adminApi.createTopic(createForm.name, createForm.description || undefined, createForm.system_prompt || undefined)
    setTopics(prev => [...prev, r.data])
    setShowCreate(false)
    setCreateForm(emptyForm)
  }

  const openEdit = (topic: AdminTopic) => {
    setEditId(topic.id)
    setEditForm({ description: topic.description ?? "", system_prompt: topic.system_prompt ?? "" })
  }

  const handleEdit = async () => {
    if (!editId) return
    const r = await adminApi.updateTopic(editId, editForm.description || undefined, editForm.system_prompt || undefined)
    setTopics(prev => prev.map(t => t.id === editId ? r.data : t))
    setEditId(null)
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this topic? This cannot be undone.")) return
    await adminApi.deleteTopic(id)
    setTopics(prev => prev.filter(t => t.id !== id))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">Topics</h2>
        <button
          onClick={() => { setShowCreate(true); setEditId(null) }}
          className="text-sm px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          + Create
        </button>
      </div>

      {showCreate && (
        <div className="bg-white border rounded p-4 mb-4">
          <h3 className="text-sm font-medium mb-3">New Topic</h3>
          <div className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="Name *"
              value={createForm.name}
              onChange={e => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
              className="border rounded px-3 py-1.5 text-sm"
            />
            <textarea
              placeholder="Description"
              value={createForm.description}
              onChange={e => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
              className="border rounded px-3 py-1.5 text-sm resize-none h-20"
            />
            <textarea
              placeholder="System prompt"
              value={createForm.system_prompt}
              onChange={e => setCreateForm(prev => ({ ...prev, system_prompt: e.target.value }))}
              className="border rounded px-3 py-1.5 text-sm resize-none h-32"
            />
            <div className="flex gap-2 mt-1">
              <button onClick={handleCreate} className="text-sm px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Save</button>
              <button onClick={() => { setShowCreate(false); setCreateForm(emptyForm) }} className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Description</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Created</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {topics.map(topic => (
              <>
                <tr key={topic.id} className="border-b last:border-0">
                  <td className="px-4 py-2 font-medium">{topic.name}</td>
                  <td className="px-4 py-2 text-gray-500 max-w-xs truncate">{topic.description ?? "—"}</td>
                  <td className="px-4 py-2 text-gray-500">{new Date(topic.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => editId === topic.id ? setEditId(null) : openEdit(topic)}
                        className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(topic.id)}
                        className="text-xs px-2 py-1 rounded border border-red-300 text-red-600 hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
                {editId === topic.id && (
                  <tr key={`edit-${topic.id}`} className="bg-gray-50 border-b">
                    <td colSpan={4} className="px-4 py-3">
                      <div className="flex flex-col gap-2 max-w-lg">
                        <p className="text-xs text-gray-500 font-medium">Name: {topic.name} (read-only)</p>
                        <textarea
                          placeholder="Description"
                          value={editForm.description}
                          onChange={e => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                          className="border rounded px-3 py-1.5 text-sm resize-none h-20"
                        />
                        <textarea
                          placeholder="System prompt"
                          value={editForm.system_prompt}
                          onChange={e => setEditForm(prev => ({ ...prev, system_prompt: e.target.value }))}
                          className="border rounded px-3 py-1.5 text-sm resize-none h-32"
                        />
                        <div className="flex gap-2">
                          <button onClick={handleEdit} className="text-sm px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Save</button>
                          <button onClick={() => setEditId(null)} className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50">Cancel</button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
