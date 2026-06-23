import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Input, Select } from '../components/FormField'
import Spinner from '../components/Spinner'
import { Salad, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'

const genderOptions = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
]

const foodPrefOptions = [
  { value: 'vegetarian',     label: 'Vegetarian' },
  { value: 'non_vegetarian', label: 'Non-Vegetarian' },
  { value: 'mixed',          label: 'Mixed' },
]

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1) // 2-step form
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const [form, setForm] = useState({
    name: '', email: '', password: '', confirm: '',
    age: '', gender: 'male', height: '', weight: '',
    food_preference: 'mixed',
  })

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const validateStep1 = () => {
    const e = {}
    if (!form.name.trim())           e.name     = 'Name required'
    if (!form.email.includes('@'))   e.email    = 'Valid email required'
    if (form.password.length < 6)   e.password = 'Minimum 6 characters'
    if (form.password !== form.confirm) e.confirm = 'Passwords do not match'
    setErrors(e)
    return !Object.keys(e).length
  }

  const validateStep2 = () => {
    const e = {}
    const age = parseInt(form.age)
    const h   = parseFloat(form.height)
    const w   = parseFloat(form.weight)
    if (!age || age < 1 || age > 120)  e.age    = 'Valid age required'
    if (!h   || h < 50  || h > 300)   e.height = 'Valid height in cm required'
    if (!w   || w < 1   || w > 500)   e.weight = 'Valid weight in kg required'
    setErrors(e)
    return !Object.keys(e).length
  }

  const handleNext = () => {
    if (validateStep1()) setStep(2)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateStep2()) return
    setLoading(true)
    try {
      await register({
        name:            form.name.trim(),
        email:           form.email.trim(),
        password:        form.password,
        age:             parseInt(form.age),
        gender:          form.gender,
        height:          parseFloat(form.height),
        weight:          parseFloat(form.weight),
        food_preference: form.food_preference,
      })
      toast.success('Account created!')
      navigate('/bmi')
    } catch (err) {
      toast.error(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-white flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4 shadow-lg">
            <Salad className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900">Create your account</h1>
          <p className="text-gray-500 mt-1">Step {step} of 2 — {step === 1 ? 'Account Details' : 'Body Measurements'}</p>
        </div>

        {/* Step indicator */}
        <div className="flex gap-2 mb-6">
          {[1, 2].map((s) => (
            <div key={s} className={`h-1.5 flex-1 rounded-full transition-colors ${s <= step ? 'bg-primary-500' : 'bg-gray-200'}`} />
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          {step === 1 ? (
            <div className="space-y-5">
              <Input label="Full Name" placeholder="John Doe" value={form.name}
                onChange={set('name')} error={errors.name} />
              <Input label="Email Address" type="email" placeholder="you@example.com"
                value={form.email} onChange={set('email')} error={errors.email} />
              <div>
                <label className="label">Password</label>
                <div className="relative">
                  <input type={showPass ? 'text' : 'password'} placeholder="Min. 6 characters"
                    className={`input-field pr-12 ${errors.password ? 'border-red-400' : ''}`}
                    value={form.password} onChange={set('password')} />
                  <button type="button" onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showPass ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
              </div>
              <Input label="Confirm Password" type="password" placeholder="Repeat password"
                value={form.confirm} onChange={set('confirm')} error={errors.confirm} />
              <button onClick={handleNext} className="btn-primary w-full py-3 text-base">
                Continue →
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input label="Age" type="number" placeholder="25" min="1" max="120"
                value={form.age} onChange={set('age')} error={errors.age} />
              <Select label="Gender" value={form.gender} onChange={set('gender')}
                options={genderOptions} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Height (cm)" type="number" placeholder="170"
                  value={form.height} onChange={set('height')} error={errors.height} />
                <Input label="Weight (kg)" type="number" placeholder="65"
                  value={form.weight} onChange={set('weight')} error={errors.weight} />
              </div>
              <Select label="Food Preference" value={form.food_preference}
                onChange={set('food_preference')} options={foodPrefOptions} />
              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setStep(1)}
                  className="btn-outline flex-1 py-3">
                  ← Back
                </button>
                <button type="submit" disabled={loading} className="btn-primary flex-1 py-3">
                  {loading ? <Spinner size="sm" /> : 'Create Account'}
                </button>
              </div>
            </form>
          )}
          <p className="text-center text-gray-500 text-sm mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 font-semibold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
