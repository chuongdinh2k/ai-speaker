import { NavLink, Outlet, useNavigate } from "react-router-dom"

export default function AdminLayout() {
  const navigate = useNavigate()

  return (
    <div className="min-h-dvh bg-gray-50 flex flex-col">
      {/* Top bar */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between max-w-4xl mx-auto w-full">
        <h1 className="text-lg font-bold">Admin</h1>
        <button
          onClick={() => navigate("/topics")}
          className="text-sm text-blue-600 hover:underline"
        >
          ← Back to app
        </button>
      </div>

      <div className="flex flex-1 max-w-4xl mx-auto w-full">
        {/* Sidebar */}
        <nav className="w-40 border-r bg-white pt-6 flex flex-col gap-1 px-3">
          <NavLink
            to="/admin/users"
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm font-medium ${isActive ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-100"}`
            }
          >
            Users
          </NavLink>
          <NavLink
            to="/admin/topics"
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm font-medium ${isActive ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-100"}`
            }
          >
            Topics
          </NavLink>
        </nav>

        {/* Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
