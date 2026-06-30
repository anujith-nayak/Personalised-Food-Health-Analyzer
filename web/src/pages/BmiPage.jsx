import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/health'
import { PageSpinner } from '../components/Spinner'
import BMIBadge from '../components/BMIBadge'
import Navbar from '../components/Navbar'
import { ArrowRight, Scale } from 'lucide-react'

const scale = [
  { range: '< 18.5',      label: 'Underweight',   color: 'bg-blue-500' },
  { range: '18.5 – 24.9', label: 'Normal Weight',  color: 'bg-green-500' },
  { range: '25 – 29.9',   label: 'Overweight',     color: 'bg-orange-500' },
  { range: '≥ 30',        label: 'Obese',          color: 'bg-red-500' },
]

export default function BmiPage() {
  const navigate = useNavigate()
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard()
      .then((r) => {
        setUser(r.data.user)
        // If health profile already exists, skip to dashboard
        if (r.data.health_profile) {
          navigate('/dashboard')
        }
      })
      .catch(() => navigate('/dashboard'))
      .finally(() => setLoading(false))
  }, [navigate])

  if (loading) return <PageSpinner />

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white">
      <Navbar />
      <div className="max-w-lg mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-2xl mb-4">
            <Scale className="w-9 h-9 text-primary-600" />
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900">Your BMI Result</h1>
          <p className="text-gray-500 mt-2">Based on your height and weight</p>
        </div>

        {/* BMI Score box */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center mb-6">
          <p className="text-gray-500 text-sm font-medium mb-2">Body Mass Index</p>
          <p className="text-7xl font-black text-primary-600 mb-4">
            {user?.bmi_score?.toFixed(1) ?? '--'}
          </p>
          {user?.bmi_category && (
            <div className="flex justify-center">
              <BMIBadge category={user.bmi_category} />
            </div>
          )}
          <div className="mt-6 pt-6 border-t border-gray-50 grid grid-cols-2 gap-4 text-sm">
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-gray-400">Height</p>
              <p className="font-bold text-gray-900">{user?.height} cm</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-gray-400">Weight</p>
              <p className="font-bold text-gray-900">{user?.weight} kg</p>
            </div>
          </div>
        </div>

        {/* Scale reference */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <h3 className="font-bold text-gray-900 mb-4">BMI Scale Reference</h3>
          <div className="space-y-3">
            {scale.map((s) => (
              <div key={s.label} className="flex items-center gap-3">
                <span className={`w-3 h-3 rounded-full flex-shrink-0 ${s.color}`} />
                <span className="text-gray-400 text-sm w-24">{s.range}</span>
                <span className={`text-sm font-semibold ${
                  s.label === user?.bmi_category ? 'text-primary-600' : 'text-gray-700'
                }`}>
                  {s.label}
                  {s.label === user?.bmi_category && ' ← You'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-gray-500 text-sm mb-6">
          Next: Tell us about your health conditions so we can personalise your food restrictions.
        </p>
        <button onClick={() => navigate('/health-assessment')}
          className="btn-primary w-full py-3.5 text-base">
          Continue to Health Assessment <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
