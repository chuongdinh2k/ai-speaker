import { useEffect, useState } from "react"
import { adminApi, type AdminUser } from "../../api/endpoints"

const ROLES = ["user", "admin"]
const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

type EditForm = { role: string; level: string; avatar_url: string }

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [passwordInputs, setPasswordInputs] = useState<Record<string, string>>({})
  const [activePasswordId, setActivePasswordId] = useState<string | null>(null)
  const [editId, setEditId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<EditForm>({ role: "", level: "", avatar_url: "" })

  useEffect(() => {
    adminApi.listUsers().then(r => setUsers(r.data))
  }, [])

  const openEdit = (user: AdminUser) => {
    setEditId(user.id)
    setEditForm({ role: user.role, level: user.level, avatar_url: user.avatar_url ?? "" })
    setActivePasswordId(null)
  }

  const handleEdit = async () => {
    if (!editId) return
    const r = await adminApi.updateUser(
      editId,
      editForm.role || undefined,
      editForm.level || undefined,
      editForm.avatar_url || undefined,
    )
    setUsers(prev => prev.map(u => u.id === editId ? r.data : u))
    setEditId(null)
  }

  const handleSetPassword = async (id: string) => {
    const password = passwordInputs[id] ?? ""
    if (!password) return
    await adminApi.updatePassword(id, password)
    setActivePasswordId(null)
    setPasswordInputs(prev => ({ ...prev, [id]: "" }))
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this user? This cannot be undone.")) return
    await adminApi.deleteUser(id)
    setUsers(prev => prev.filter(u => u.id !== id))
  }

  return (
    <div>
      <h2 className="text-base font-semibold mb-4">Users</h2>
      <div className="bg-white rounded border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Role</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Level</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Created</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <>
                <tr key={user.id} className="border-b last:border-0">
                  <td className="px-4 py-2">{user.email}</td>
                  <td className="px-4 py-2">{user.role}</td>
                  <td className="px-4 py-2">{user.level}</td>
                  <td className="px-4 py-2 text-gray-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => editId === user.id ? setEditId(null) : openEdit(user)}
                        className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          setActivePasswordId(activePasswordId === user.id ? null : user.id)
                          setEditId(null)
                        }}
                        className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                      >
                        Set Password
                      </button>
                      <button
                        onClick={() => handleDelete(user.id)}
                        className="text-xs px-2 py-1 rounded border border-red-300 text-red-600 hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
                {editId === user.id && (
                  <tr key={`edit-${user.id}`} className="bg-gray-50 border-b">
                    <td colSpan={5} className="px-4 py-3">
                      <div className="flex flex-wrap gap-3 items-end">
                        <div className="flex flex-col gap-1">
                          <label className="text-xs text-gray-500">Role</label>
                          <select
                            value={editForm.role}
                            onChange={e => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                            className="border rounded px-2 py-1 text-sm"
                          >
                            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                          </select>
                        </div>
                        <div className="flex flex-col gap-1">
                          <label className="text-xs text-gray-500">Level</label>
                          <select
                            value={editForm.level}
                            onChange={e => setEditForm(prev => ({ ...prev, level: e.target.value }))}
                            className="border rounded px-2 py-1 text-sm"
                          >
                            {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                          </select>
                        </div>
                        <div className="flex flex-col gap-1 flex-1 min-w-[200px]">
                          <label className="text-xs text-gray-500">Avatar URL</label>
                          <input
                            type="text"
                            placeholder="https://..."
                            value={editForm.avatar_url}
                            onChange={e => setEditForm(prev => ({ ...prev, avatar_url: e.target.value }))}
                            className="border rounded px-2 py-1 text-sm"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button onClick={handleEdit} className="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Save</button>
                          <button onClick={() => setEditId(null)} className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50">Cancel</button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                {activePasswordId === user.id && (
                  <tr key={`pw-${user.id}`} className="bg-gray-50 border-b">
                    <td colSpan={5} className="px-4 py-2">
                      <div className="flex gap-2 items-center">
                        <input
                          type="password"
                          placeholder="New password"
                          value={passwordInputs[user.id] ?? ""}
                          onChange={e => setPasswordInputs(prev => ({ ...prev, [user.id]: e.target.value }))}
                          className="border rounded px-2 py-1 text-sm flex-1 max-w-xs"
                        />
                        <button
                          onClick={() => handleSetPassword(user.id)}
                          className="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setActivePasswordId(null)}
                          className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                        >
                          Cancel
                        </button>
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
