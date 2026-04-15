import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import LoginPage from "./pages/LoginPage"
import TopicsPage from "./pages/TopicsPage"
import ChatPage from "./pages/ChatPage"
import VocabularyPage from "./pages/VocabularyPage"

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token")
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/topics" element={<PrivateRoute><TopicsPage /></PrivateRoute>} />
        <Route path="/chat/:conversationId" element={<PrivateRoute><ChatPage /></PrivateRoute>} />
        <Route path="/topics/:topicId/vocabulary" element={<PrivateRoute><VocabularyPage /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/topics" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
