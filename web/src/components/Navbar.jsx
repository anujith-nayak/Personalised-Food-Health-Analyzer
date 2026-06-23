import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Salad, LogOut, LayoutDashboard, ScanLine } from 'lucide-react'

export default function Navbar() {
  const { authenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-gray-100 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to={authenticated ? '/dashboard' : '/'} className="flex items-center gap-2 font-bold text-xl text-primary-700">
            <Salad className="w-7 h-7 text-primary-600" />
            FoodHealth AI
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-2">
            {authenticated ? (
              <>
                <Link to="/dashboard" className="btn-ghost hidden sm:flex items-center gap-1.5 text-sm">
                  <LayoutDashboard className="w-4 h-4" /> Dashboard
                </Link>
                <Link to="/scan" className="btn-ghost hidden sm:flex items-center gap-1.5 text-sm">
                  <ScanLine className="w-4 h-4" /> Scan Food
                </Link>
                <button onClick={handleLogout} className="btn-ghost flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50">
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login"    className="btn-ghost text-sm">Login</Link>
                <Link to="/register" className="btn-primary text-sm py-2 px-4">Get Started</Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
