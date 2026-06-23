import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard, updateProfile, updateHealthProfile } from '../api/health'
import { PageSpinner } from '../components/Spinner'
import Spinner from '../components/Spinner'
import Navbar from '../components/Navbar'
import { Input, Select } from '../components/FormField'
import toast from 'react-hot-toast'
import { User, HeartPulse, Activity, CheckCircle2 } from 'lucide-react'

const foodPrefOptions = [
  { value: 'vegetarian',     label: 'Vegetarian' },
  { value: 'non_vegetarian', label: 'Non-Vegetarian' },
  { value: 'mixed',          label: 'Mixed' },
]

const CONDITIONS = ['Hypertension (BP)', 'Diabetes', 'PCOS', 'PCOD', 'Thyroid', 'Heart Disease', 'Kidney Disease', 'Obesity', 'None']
const STATUSES   = ['Normal', 'Fever', 'Cold', 'Cough', 'Stomach Upset', 'Vomiting', 'Diarrhea', 'Weakness', 'Headache', 'Other']

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl transition-all
        ${active ? 'bg-primary-600 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-100'}`}>
      <Icon className="w-4 h-4" /> {label}
    </button>
  )
}

function ChipToggle({ options, selected, onToggle, exclusive = false }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isSel = selected.includes(opt)
        const isOff = exclusive && selected.includes('None') && opt !== 'None'
        return (
          <button key={opt} type="button" disabled={isOff} onClick={() => onToggle(opt)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border-2 transition-all
              ${isSel ? 'bg-primary-600 border-primary-600 text-white'
                : isOff ? 'bg-gray-50 border-gray-200 text-gray-300 cursor-not-allowed'
                : 'bg-white border-gray-200 text-gray-700 hover:border-primary-400'}`}>
            {isSel && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1 -mt-0.5" />}
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function RadioRow({ label, options, value, onChange }) {
  return (
    <div className="mb-3">
      <p className="text-xs font-semibold text-gray-600 mb-2">{label}</p>
      <div className="flex flex-wrap gap-4">
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 capitalize">
            <input type="radio" value={o} checked={value === o} onChange={() => onChange(o)}
              className="text-primary-600 focus:ring-primary-500" />
            {o}
          </label>
        ))}
      </div>
    </div>
  )
}

export default function EditProfilePage() {
  const navigate = useNavigate()
  const [tab, setTab]       = useState('profile')
  const [initLoading, setInitLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Profile tab
  const [weight, setWeight]   = useState('')
  const [height, setHeight]   = useState('')
  const [age, setAge]         = useState('')
  const [foodPref, setFoodPref] = useState('mixed')

  // Health tab
  const [conditions, setConditions] = useState([])
  const [bpStatus,   setBpStatus]   = useState('normal')
  const [systolic,   setSystolic]   = useState('')
  const [diastolic,  setDiastolic]  = useState('')
  const [sugarStatus, setSugarStatus] = useState('normal')
  const [fastingSugar, setFastingSugar] = useState('')
  const [postMealSugar, setPostMealSugar] = useState('')
  const [thyroidType, setThyroidType] = useState('hypothyroidism')
  const [pcosDiagnosed, setPcosDiagnosed] = useState(null)
  const [pcodDiagnosed, setPcodDiagnosed] = useState(null)

  // Status tab
  const [statuses, setStatuses] = useState([])

  useEffect(() => {
    getDashboard().then((res) => {
      const { user, health_profile: hp, current_health_statuses } = res.data
      setWeight(user.weight.toString())
      setHeight(user.height.toString())
      setAge(user.age.toString())
      setFoodPref(user.food_preference)

      if (hp) {
        const active = []
        if (hp.hypertension)  { active.push('Hypertension (BP)'); setBpStatus(hp.bp_status || 'normal'); setSystolic(hp.systolic?.toString() || ''); setDiastolic(hp.diastolic?.toString() || '') }
        if (hp.diabetes)      { active.push('Diabetes'); setSugarStatus(hp.sugar_status || 'normal'); setFastingSugar(hp.fasting_sugar?.toString() || ''); setPostMealSugar(hp.post_meal_sugar?.toString() || '') }
        if (hp.thyroid)       { active.push('Thyroid'); setThyroidType(hp.thyroid_type || 'hypothyroidism') }
        if (hp.pcos)          { active.push('PCOS'); setPcosDiagnosed(hp.pcos_diagnosed ?? null) }
        if (hp.pcod)          { active.push('PCOD'); setPcodDiagnosed(hp.pcod_diagnosed ?? null) }
        if (hp.heart_disease) active.push('Heart Disease')
        if (hp.kidney_disease) active.push('Kidney Disease')
        if (hp.obesity)       active.push('Obesity')
        if (hp.none)          active.push('None')
        setConditions(active)
      }
      setStatuses(current_health_statuses || [])
    }).catch(() => toast.error('Failed to load profile'))
      .finally(() => setInitLoading(false))
  }, [])

  const toggleCondition = (c) => {
    if (c === 'None') { setConditions(['None']); return }
    setConditions((p) => p.includes(c) ? p.filter((x) => x !== c) : [...p.filter((x) => x !== 'None'), c])
  }
  const toggleStatus = (s) => setStatuses((p) => p.includes(s) ? p.filter((x) => x !== s) : [...p, s])

  const saveProfile = async () => {
    setSaving(true)
    try {
      await updateProfile({ weight: parseFloat(weight), height: parseFloat(height), age: parseInt(age), food_preference: foodPref })
      toast.success('Profile updated!')
    } catch (err) { toast.error(err.message) }
    finally { setSaving(false) }
  }

  const saveHealth = async () => {
    setSaving(true)
    try {
      const has = (c) => conditions.includes(c)
      const payload = {
        hypertension: has('Hypertension (BP)'), diabetes: has('Diabetes'),
        thyroid: has('Thyroid'), pcos: has('PCOS'), pcod: has('PCOD'),
        heart_disease: has('Heart Disease'), kidney_disease: has('Kidney Disease'),
        obesity: has('Obesity'), none: has('None'),
        current_health_statuses: statuses,
      }
      if (has('Hypertension (BP)')) { payload.bp_status = bpStatus; if (systolic) payload.systolic = parseInt(systolic); if (diastolic) payload.diastolic = parseInt(diastolic) }
      if (has('Diabetes')) { payload.sugar_status = sugarStatus; if (fastingSugar) payload.fasting_sugar = parseFloat(fastingSugar); if (postMealSugar) payload.post_meal_sugar = parseFloat(postMealSugar) }
      if (has('Thyroid')) payload.thyroid_type = thyroidType
      if (has('PCOS') && pcosDiagnosed !== null) payload.pcos_diagnosed = pcosDiagnosed
      if (has('PCOD') && pcodDiagnosed !== null) payload.pcod_diagnosed = pcodDiagnosed
      await updateHealthProfile(payload)
      toast.success('Health profile updated!')
    } catch (err) { toast.error(err.message) }
    finally { setSaving(false) }
  }

  if (initLoading) return <PageSpinner />

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-gray-900 mb-1">Edit Profile</h1>
          <p className="text-gray-500 text-sm">Update your details and health information</p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-2 bg-gray-100 p-1.5 rounded-2xl mb-6">
          <TabButton active={tab === 'profile'} onClick={() => setTab('profile')} icon={User}      label="Profile" />
          <TabButton active={tab === 'health'}  onClick={() => setTab('health')}  icon={HeartPulse} label="Health Conditions" />
          <TabButton active={tab === 'status'}  onClick={() => setTab('status')}  icon={Activity}   label="Current Status" />
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">

          {/* ── Profile Tab ───────────────────────────────────────────────── */}
          {tab === 'profile' && (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <Input label="Weight (kg)" type="number" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="65" />
                <Input label="Height (cm)" type="number" value={height} onChange={(e) => setHeight(e.target.value)} placeholder="170" />
              </div>
              <Input label="Age" type="number" value={age} onChange={(e) => setAge(e.target.value)} placeholder="25" />
              <Select label="Food Preference" value={foodPref} onChange={(e) => setFoodPref(e.target.value)} options={foodPrefOptions} />
              <button onClick={saveProfile} disabled={saving} className="btn-primary w-full py-3">
                {saving ? <Spinner size="sm" /> : 'Save Profile'}
              </button>
            </div>
          )}

          {/* ── Health Tab ────────────────────────────────────────────────── */}
          {tab === 'health' && (
            <div className="space-y-5">
              <div>
                <p className="label mb-3">Health Conditions</p>
                <ChipToggle options={CONDITIONS} selected={conditions} onToggle={toggleCondition} exclusive />
              </div>

              {conditions.includes('Hypertension (BP)') && (
                <div className="bg-primary-50 rounded-xl p-4 border border-primary-100">
                  <p className="font-semibold text-primary-800 text-sm mb-3">Hypertension Details</p>
                  <RadioRow label="BP Status" options={['normal', 'low', 'high']} value={bpStatus} onChange={setBpStatus} />
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <Input label="Systolic (mmHg)" type="number" value={systolic} onChange={(e) => setSystolic(e.target.value)} placeholder="120" />
                    <Input label="Diastolic (mmHg)" type="number" value={diastolic} onChange={(e) => setDiastolic(e.target.value)} placeholder="80" />
                  </div>
                </div>
              )}

              {conditions.includes('Diabetes') && (
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                  <p className="font-semibold text-orange-800 text-sm mb-3">Diabetes Details</p>
                  <RadioRow label="Sugar Status" options={['normal', 'low', 'high']} value={sugarStatus} onChange={setSugarStatus} />
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <Input label="Fasting Sugar" type="number" value={fastingSugar} onChange={(e) => setFastingSugar(e.target.value)} placeholder="90" />
                    <Input label="Post Meal Sugar" type="number" value={postMealSugar} onChange={(e) => setPostMealSugar(e.target.value)} placeholder="140" />
                  </div>
                </div>
              )}

              {conditions.includes('Thyroid') && (
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="font-semibold text-blue-800 text-sm mb-3">Thyroid Type</p>
                  <RadioRow label="" options={['hypothyroidism', 'hyperthyroidism']} value={thyroidType} onChange={setThyroidType} />
                </div>
              )}

              {conditions.includes('PCOS') && (
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="font-semibold text-purple-800 text-sm mb-3">PCOS — Diagnosed?</p>
                  <RadioRow label="" options={['yes', 'no']} value={pcosDiagnosed === true ? 'yes' : pcosDiagnosed === false ? 'no' : ''} onChange={(v) => setPcosDiagnosed(v === 'yes')} />
                </div>
              )}

              {conditions.includes('PCOD') && (
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="font-semibold text-purple-800 text-sm mb-3">PCOD — Diagnosed?</p>
                  <RadioRow label="" options={['yes', 'no']} value={pcodDiagnosed === true ? 'yes' : pcodDiagnosed === false ? 'no' : ''} onChange={(v) => setPcodDiagnosed(v === 'yes')} />
                </div>
              )}

              <button onClick={saveHealth} disabled={saving} className="btn-primary w-full py-3">
                {saving ? <Spinner size="sm" /> : 'Save Health Conditions'}
              </button>
            </div>
          )}

          {/* ── Status Tab ────────────────────────────────────────────────── */}
          {tab === 'status' && (
            <div className="space-y-5">
              <div>
                <p className="label mb-3">Current Health Status</p>
                <ChipToggle options={STATUSES} selected={statuses} onToggle={toggleStatus} />
              </div>
              <button onClick={saveHealth} disabled={saving} className="btn-primary w-full py-3">
                {saving ? <Spinner size="sm" /> : 'Save Status'}
              </button>
            </div>
          )}
        </div>

        <button onClick={() => navigate('/dashboard')} className="btn-ghost w-full mt-4 text-center text-sm">
          ← Back to Dashboard
        </button>
      </div>
    </div>
  )
}
