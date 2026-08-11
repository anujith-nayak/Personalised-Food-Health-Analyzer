import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LandingPage   from './pages/LandingPage'
import LoginPage     from './pages/LoginPage'
import RegisterPage  from './pages/RegisterPage'
import BmiPage       from './pages/BmiPage'
import HealthAssessmentPage from './pages/HealthAssessmentPage'
import DashboardPage from './pages/DashboardPage'
import EditProfilePage from './pages/EditProfilePage'
import ScanPage      from './pages/ScanPage'
import BloodReportPage from './pages/BloodReportPage'

function PrivateRoute({ children }) {
  const { authenticated } = useAuth()
  return authenticated ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { authenticated } = useAuth()
  return authenticated ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/"         element={<LandingPage />} />
        <Route path="/login"    element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/bmi"      element={<PrivateRoute><BmiPage /></PrivateRoute>} />
        <Route path="/health-assessment" element={<PrivateRoute><HealthAssessmentPage /></PrivateRoute>} />
        <Route path="/blood-report" element={<PrivateRoute><BloodReportPage /></PrivateRoute>} />
        <Route path="/dashboard"   element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
        <Route path="/edit-profile" element={<PrivateRoute><EditProfilePage /></PrivateRoute>} />
        <Route path="/scan"        element={<PrivateRoute><ScanPage /></PrivateRoute>} />
        <Route path="*"            element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
