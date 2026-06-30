import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../api/health'
import { PageSpinner } from '../components/Spinner'
import Navbar from '../components/Navbar'
import Card, { CardHeader } from '../components/Card'
import BMIBadge from '../components/BMIBadge'
import {
  User, Scale, HeartPulse, Activity,
  ShieldAlert, ScanLine, Pencil, RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-50 last:border-0">
      <span className="text-gray-500 text-sm">{label}</span>
      <span className="font-semibold text-gray-900 text-sm capitalize">{value}</span>
    </div>
  )
}

function Chip({ label, color = 'gray' }) {
  const colors = {
    gray:   'bg-gray-100 text-gray-700',
    green:  'bg-green-100 text-green-700',
    red:    'bg-red-100 text-red-700',
    blue:   'bg-blue-100 text-blue-700',
    orange: 'bg-orange-100 text-orange-700',
  }
  return <span className={`chip text-xs font-medium px-3 py-1.5 rounded-full ${colors[color] || colors.gray}`}>{label}</span>
}

export default function DashboardPage() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    try {
      const res = await getDashboard()
      setData(res.data)
    } catch {
      toast.error('Failed to load dashboard')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <PageSpinner />

  // If data failed to load, show error state instead of crashing
  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <p className="text-gray-500">Could not load dashboard. Is the backend running?</p>
          <button onClick={() => load()} className="btn-primary px-6 py-2">Retry</button>
        </div>
      </div>
    )
  }

  const { user, health_profile: hp, current_health_statuses: statuses, profile_completion: completion } = data

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-extrabold text-gray-900">Good day, {user.name.split(' ')[0]} 👋</h1>
            <p className="text-gray-500 mt-0.5">Here's your health overview</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => load(true)} className="btn-ghost flex items-center gap-2 text-sm border border-gray-200">
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <Link to="/edit-profile" className="btn-outline text-sm py-2 px-4">
              <Pencil className="w-4 h-4" /> Edit Profile
            </Link>
            <Link to="/scan" className="btn-primary text-sm py-2 px-4">
              <ScanLine className="w-4 h-4" /> Scan Food
            </Link>
          </div>
        </div>

        {/* Profile Completion bar */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700">Profile Completion</span>
            <span className="text-sm font-bold text-primary-600">{completion}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5">
            <div className="bg-primary-600 h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${completion}%` }} />
          </div>
          {completion < 100 && (
            <p className="text-xs text-gray-400 mt-2">
              {!hp ? '· Complete your health assessment' : '· Add your current health status'}
            </p>
          )}
        </div>

        {/* Main grid */}
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Left column */}
          <div className="lg:col-span-1 space-y-6">

            {/* Profile */}
            <Card>
              <CardHeader icon={User} title="Profile" />
              <div className="p-6">
                <InfoRow label="Name"            value={user.name} />
                <InfoRow label="Age"             value={`${user.age} years`} />
                <InfoRow label="Gender"          value={user.gender} />
                <InfoRow label="Height"          value={`${user.height} cm`} />
                <InfoRow label="Weight"          value={`${user.weight} kg`} />
                <InfoRow label="Food Preference" value={user.food_preference.replace('_', ' ')} />
              </div>
            </Card>

            {/* BMI */}
            <Card>
              <CardHeader icon={Scale} title="BMI" />
              <div className="p-6 text-center">
                <p className="text-5xl font-black text-primary-600 mb-3">
                  {user.bmi_score?.toFixed(1) ?? '--'}
                </p>
                {user.bmi_category && <BMIBadge category={user.bmi_category} />}
              </div>
            </Card>
          </div>

          {/* Right column */}
          <div className="lg:col-span-2 space-y-6">

            {/* Health Conditions */}
            <Card>
              <CardHeader icon={HeartPulse} title="Health Conditions" />
              <div className="p-6">
                {hp ? (
                  hp.hypertension || hp.diabetes || hp.thyroid || hp.pcos || hp.pcod ||
                  hp.heart_disease || hp.kidney_disease || hp.obesity ? (
                    <div className="flex flex-wrap gap-2">
                      {hp.hypertension  && <Chip label="Hypertension (BP)" color="red" />}
                      {hp.diabetes      && <Chip label="Diabetes"           color="orange" />}
                      {hp.thyroid       && <Chip label="Thyroid"            color="blue" />}
                      {hp.pcos          && <Chip label="PCOS"               color="blue" />}
                      {hp.pcod          && <Chip label="PCOD"               color="blue" />}
                      {hp.heart_disease && <Chip label="Heart Disease"      color="red" />}
                      {hp.kidney_disease && <Chip label="Kidney Disease"    color="orange" />}
                      {hp.obesity       && <Chip label="Obesity"            color="orange" />}
                    </div>
                  ) : <Chip label="None selected" color="green" />
                ) : (
                  <div className="text-center py-4">
                    <p className="text-gray-400 text-sm mb-3">No health assessment yet</p>
                    <Link to="/health-assessment" className="btn-primary text-sm py-2 px-4">
                      Complete Assessment
                    </Link>
                  </div>
                )}
              </div>
            </Card>

            {/* Current Health Status */}
            <Card>
              <CardHeader icon={Activity} title="Current Health Status" />
              <div className="p-6">
                {statuses.length ? (
                  <div className="flex flex-wrap gap-2">
                    {statuses.map((s) => <Chip key={s} label={s} color={s === 'Normal' ? 'green' : 'orange'} />)}
                  </div>
                ) : <p className="text-gray-400 text-sm">No status recorded</p>}
              </div>
            </Card>

            {/* Food Restrictions */}
            <Card>
              <CardHeader icon={ShieldAlert} title="Food Restrictions" color="text-red-500" />
              <div className="p-6">
                {data.food_restriction_groups && data.food_restriction_groups.length > 0 ? (
                  <div className="space-y-5">
                    {data.food_restriction_groups.map((group) => (
                      <div key={group.category}>
                        <p className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                          {group.category}
                        </p>
                        <div className="grid sm:grid-cols-2 gap-1.5 pl-4">
                          {group.items.map((item) => (
                            <div key={item} className="flex items-center gap-2 bg-red-50 rounded-lg px-3 py-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                              <span className="text-sm text-red-800">{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm">
                    {hp ? 'No restrictions — all clear!' : 'Complete health assessment to see restrictions'}
                  </p>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
