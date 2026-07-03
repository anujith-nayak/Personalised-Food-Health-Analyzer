import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Salad, LogOut, LayoutDashboard, ScanLine, Menu, X } from 'lucide-react'

export default function Navbar() {
  const { authenticated, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
    setMenuOpen(false)
  }

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14 sm:h-16">

          {/* Logo */}
          <Link
            to={authenticated ? '/dashboard' : '/'}
            className="flex items-center gap-2 font-bold text-lg sm:text-xl text-primary-700"
            onClick={() => setMenuOpen(false)}
          >
            <Salad className="w-6 h-6 sm:w-7 sm:h-7 text-primary-600" />
            <span>FoodHealth AI</span>
          </Link>

          {/* Desktop links */}
          <div className="hidden sm:flex items-center gap-2">
            {authenticated ? (
              <>
                <Link to="/dashboard" className="btn-ghost flex items-center gap-1.5 text-sm">
                  <LayoutDashboard className="w-4 h-4" /> Dashboard
                </Link>
                <Link to="/scan" className="btn-ghost flex items-center gap-1.5 text-sm">
                  <ScanLine className="w-4 h-4" /> Scan Food
                </Link>
                <button onClick={handleLogout}
                  className="btn-ghost flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50">
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

          {/* Mobile hamburger */}
          <button
            className="sm:hidden p-2 rounded-xl hover:bg-gray-100 active:bg-gray-200"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div className="sm:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1">
          {authenticated ? (
            <>
              <Link to="/dashboard" onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-gray-50 text-gray-700 font-medium">
                <LayoutDashboard className="w-5 h-5 text-primary-600" /> Dashboard
              </Link>
              <Link to="/scan" onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-gray-50 text-gray-700 font-medium">
                <ScanLine className="w-5 h-5 text-primary-600" /> Scan Food
              </Link>
              <button onClick={handleLogout}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-red-50 text-red-600 font-medium">
                <LogOut className="w-5 h-5" /> Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={() => setMenuOpen(false)}
                className="flex items-center px-3 py-3 rounded-xl hover:bg-gray-50 text-gray-700 font-medium">
                Login
              </Link>
              <Link to="/register" onClick={() => setMenuOpen(false)}
                className="btn-primary w-full py-3 text-base">
                Get Started
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  )
}
