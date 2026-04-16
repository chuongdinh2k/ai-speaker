import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute"
import LoginPage from "./pages/LoginPage"
import TopicsPage from "./pages/TopicsPage"
import ChatPage from "./pages/ChatPage"
import VocabularyPage from "./pages/VocabularyPage"
import ProfilePage from "./pages/ProfilePage"
import GlobalVocabularyPage from "./pages/GlobalVocabularyPage"
import AdminLayout from "./pages/admin/AdminLayout"
import AdminUsersPage from "./pages/admin/AdminUsersPage"
import AdminTopicsPage from "./pages/admin/AdminTopicsPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/topics" element={<ProtectedRoute><TopicsPage /></ProtectedRoute>} />
        <Route path="/chat/:conversationId" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
        <Route path="/topics/:topicId/vocabulary" element={<ProtectedRoute><VocabularyPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/vocabulary" element={<ProtectedRoute><GlobalVocabularyPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute requiredRole="admin"><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/admin/users" replace />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="topics" element={<AdminTopicsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/topics" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
