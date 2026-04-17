import { useEffect, useState } from "react"
import { adminApi, type AdminUser } from "../../api/endpoints"

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [passwordInputs, setPasswordInputs] = useState<Record<string, string>>({})
  const [activePasswordId, setActivePasswordId] = useState<string | null>(null)

  useEffect(() => {
    adminApi.listUsers().then(r => setUsers(r.data))
  }, [])

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
                        onClick={() => setActivePasswordId(activePasswordId === user.id ? null : user.id)}
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
