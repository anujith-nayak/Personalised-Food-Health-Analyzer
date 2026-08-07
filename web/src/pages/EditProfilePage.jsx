import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard, updateProfile, updateHealthProfile } from '../api/health'
import { PageSpinner } from '../components/Spinner'
import Spinner from '../components/Spinner'
import Navbar from '../components/Navbar'
import { Input, Select } from '../components/FormField'
import toast from 'react-hot-toast'
import { User, HeartPulse, Activity, CheckCircle2, AlertCircle } from 'lucide-react'

const foodPrefOptions = [
  { value: 'vegetarian',     label: 'Vegetarian' },
  { value: 'non_vegetarian', label: 'Non-Vegetarian' },
  { value: 'mixed',          label: 'Mixed' },
]
const ALL_CONDITIONS = [
  'Hypertension (BP)', 'Diabetes', 'PCOS', 'PCOD',
  'Thyroid', 'Heart Disease', 'Kidney Disease', 'Obesity',
  'High Cholesterol', 'Appendicitis', 'Other', 'None',
]
const FEMALE_ONLY = ['PCOS', 'PCOD']
const STATUSES = [
  'Normal', 'Fever', 'Cold', 'Cough', 'Stomach Upset',
  'Vomiting', 'Diarrhea', 'Weakness', 'Headache', 'Other',
]
const BP_RANGES = {
  low:  { systolic: [0, 89],    diastolic: [0, 59] },
  high: { systolic: [121, 300], diastolic: [81, 200] },
}
const SUGAR_RANGES = {
  low:  { fasting: [0, 69],    post_meal: [0, 79] },
  high: { fasting: [100, 600], post_meal: [140, 600] },
}
function validateBP(status, sys, dia) {
  if (status === 'normal' || !BP_RANGES[status]) return null
  const r = BP_RANGES[status]
  if (sys) { const [lo, hi] = r.systolic; if (sys < lo || sys > hi) return `Systolic ${sys} mmHg doesn't match "${status}" BP (${lo}–${hi} mmHg).` }
  if (dia) { const [lo, hi] = r.diastolic; if (dia < lo || dia > hi) return `Diastolic ${dia} mmHg doesn't match "${status}" BP (${lo}–${hi} mmHg).` }
  return null
}
function validateSugar(status, fasting, postMeal) {
  if (status === 'normal' || !SUGAR_RANGES[status]) return null
  const r = SUGAR_RANGES[status]
  if (fasting) { const [lo, hi] = r.fasting; if (fasting < lo || fasting > hi) return `Fasting sugar ${fasting} doesn't match "${status}" range (${lo}–${hi}).` }
  if (postMeal) { const [lo, hi] = r.post_meal; if (postMeal < lo || postMeal > hi) return `Post-meal sugar ${postMeal} doesn't match "${status}" range (${lo}–${hi}).` }
  return null
}

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-xl transition-all flex-1 justify-center
        ${active ? 'bg-primary-600 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-100'}`}>
      <Icon className="w-4 h-4" /> {label}
    </button>
  )
}
function ChipToggle({ options, selected, onToggle, disabledOptions = [] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isSel = selected.includes(opt)
        const isNoneBlock = selected.includes('None') && opt !== 'None'
        const isDisabled = disabledOptions.includes(opt) || isNoneBlock
        return (
          <button key={opt} type="button" disabled={isDisabled} onClick={() => onToggle(opt)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border-2 transition-all
              ${isSel ? 'bg-primary-600 border-primary-600 text-white'
                : isDisabled ? 'bg-gray-100 border-gray-200 text-gray-300 cursor-not-allowed line-through'
                : 'bg-white border-gray-200 text-gray-700 hover:border-primary-400'}`}>
            {isSel && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1 -mt-0.5" />}
            {opt}
            {disabledOptions.includes(opt) && <span className="text-xs ml-1">(N/A)</span>}
          </button>
        )
      })}
    </div>
  )
}
function RadioRow({ label, options, value, onChange }) {
  return (
    <div className="mb-2">
      {label && <p className="text-xs font-semibold text-gray-600 mb-2">{label}</p>}
      <div className="flex flex-wrap gap-4">
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer text-sm capitalize">
            <input type="radio" value={o} checked={value === o} onChange={() => onChange(o)} className="accent-primary-600" />
            {o.replace('_', ' ')}
          </label>
        ))}
      </div>
    </div>
  )
}
function ValidationError({ msg }) {
  if (!msg) return null
  return (
    <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mt-2">
      <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
      <p className="text-red-700 text-sm">{msg}</p>
    </div>
  )
}

export default function EditProfilePage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('profile')
  const [initLoading, setInitLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [userGender, setUserGender] = useState(null)

  // Profile tab
  const [weight,   setWeight]   = useState('')
  const [height,   setHeight]   = useState('')
  const [age,      setAge]      = useState('')
  const [foodPref, setFoodPref] = useState('mixed')

  // Health tab
  const [conditions,    setConditions]    = useState([])
  const [bpStatus,      setBpStatus]      = useState('normal')
  const [systolic,      setSystolic]      = useState('')
  const [diastolic,     setDiastolic]     = useState('')
  const [bpError,       setBpError]       = useState(null)
  const [sugarStatus,   setSugarStatus]   = useState('normal')
  const [fastingSugar,  setFastingSugar]  = useState('')
  const [postMealSugar, setPostMealSugar] = useState('')
  const [sugarError,    setSugarError]    = useState(null)
  const [thyroidType,   setThyroidType]   = useState('hypothyroidism')
  const [pcosDiagnosed, setPcosDiagnosed] = useState(null)
  const [pcodDiagnosed, setPcodDiagnosed] = useState(null)
  const [appendicitisPhase, setAppendicitisPhase] = useState('acute')
  const [otherCondition, setOtherCondition] = useState('')
  const [otherStatus, setOtherStatus] = useState('')

  // Status tab
  const [statuses, setStatuses] = useState([])

  const disabledForGender = userGender === 'male' ? FEMALE_ONLY : []

  useEffect(() => {
    getDashboard().then((res) => {
      const { user, health_profile: hp, current_health_statuses } = res.data
      setUserGender(user.gender)
      setWeight(user.weight.toString())
      setHeight(user.height.toString())
      setAge(user.age.toString())
      setFoodPref(user.food_preference)

      if (hp) {
        const active = []
        if (hp.hypertension)  { active.push('Hypertension (BP)'); setBpStatus(hp.bp_status || 'normal'); setSystolic(hp.systolic?.toString() || ''); setDiastolic(hp.diastolic?.toString() || '') }
        if (hp.diabetes)      { active.push('Diabetes'); setSugarStatus(hp.sugar_status || 'normal'); setFastingSugar(hp.fasting_sugar?.toString() || ''); setPostMealSugar(hp.post_meal_sugar?.toString() || '') }
        if (hp.thyroid)       { active.push('Thyroid'); setThyroidType(hp.thyroid_type || 'hypothyroidism') }
        if (hp.pcos)          { active.push('PCOS');    setPcosDiagnosed(hp.pcos_diagnosed ?? null) }
        if (hp.pcod)          { active.push('PCOD');    setPcodDiagnosed(hp.pcod_diagnosed ?? null) }
        if (hp.heart_disease)  active.push('Heart Disease')
        if (hp.kidney_disease) active.push('Kidney Disease')
        if (hp.obesity)        active.push('Obesity')
        if (hp.high_cholesterol) active.push('High Cholesterol')
        if (hp.appendicitis)  { active.push('Appendicitis'); setAppendicitisPhase(hp.appendicitis_phase || 'acute') }
        if (hp.other_condition) { active.push('Other'); setOtherCondition(hp.other_condition) }
        if (hp.none)           active.push('None')
        if (hp.other_status)   setOtherStatus(hp.other_status)
        setConditions(active)
      }
      setStatuses(current_health_statuses || [])
    }).catch(() => toast.error('Failed to load profile'))
      .finally(() => setInitLoading(false))
  }, [])

  const toggleCondition = (c) => {
    if (disabledForGender.includes(c)) return
    if (c === 'None') { setConditions((p) => p.includes('None') ? [] : ['None']); return }
    setConditions((p) => {
      const next = p.includes(c) ? p.filter((x) => x !== c) : [...p.filter((x) => x !== 'None'), c]
      if (c === 'Other' && p.includes('Other')) setOtherCondition('')
      return next
    })
  }
  const toggleStatus = (s) =>
    setStatuses((p) => p.includes(s) ? p.filter((x) => x !== s) : [...p, s])

  const handleBpStatusChange = (v) => { setBpStatus(v); setBpError(null); setSystolic(''); setDiastolic('') }
  const handleSugarStatusChange = (v) => { setSugarStatus(v); setSugarError(null); setFastingSugar(''); setPostMealSugar('') }

  const saveProfile = async () => {
    if (!weight || parseFloat(weight) <= 0) { toast.error('Enter a valid weight'); return }
    if (!height || parseFloat(height) <= 0) { toast.error('Enter a valid height'); return }
    if (!age    || parseInt(age) <= 0)       { toast.error('Enter a valid age');    return }
    setSaving(true)
    try {
      await updateProfile({ weight: parseFloat(weight), height: parseFloat(height), age: parseInt(age), food_preference: foodPref })
      toast.success('Profile updated!')
      navigate('/dashboard')
    } catch (err) { toast.error(err.message || 'Failed to update') }
    finally { setSaving(false) }
  }

  const saveHealth = async () => {
    let valid = true
    if (conditions.includes('Hypertension (BP)') && bpStatus !== 'normal') {
      if (!systolic)  { setBpError('Systolic required for ' + bpStatus + ' BP'); valid = false }
      else if (!diastolic) { setBpError('Diastolic required for ' + bpStatus + ' BP'); valid = false }
      else { const err = validateBP(bpStatus, parseInt(systolic), parseInt(diastolic)); if (err) { setBpError(err); valid = false } }
    }
    if (conditions.includes('Diabetes') && sugarStatus !== 'normal') {
      if (!fastingSugar)  { setSugarError('Fasting sugar required'); valid = false }
      else if (!postMealSugar) { setSugarError('Post meal sugar required'); valid = false }
      else { const err = validateSugar(sugarStatus, parseFloat(fastingSugar), parseFloat(postMealSugar)); if (err) { setSugarError(err); valid = false } }
    }
    if (!valid) { toast.error('Please fill in required values'); return }

    setSaving(true)
    try {
      const has = (c) => conditions.includes(c)
      const payload = {
        hypertension:    has('Hypertension (BP)'),
        diabetes:        has('Diabetes'),
        thyroid:         has('Thyroid'),
        pcos:            has('PCOS'),
        pcod:            has('PCOD'),
        heart_disease:   has('Heart Disease'),
        kidney_disease:  has('Kidney Disease'),
        obesity:         has('Obesity'),
        high_cholesterol: has('High Cholesterol'),
        appendicitis:    has('Appendicitis'),
        none:            has('None'),
        current_health_statuses: statuses,
      }
      if (has('Hypertension (BP)')) {
        payload.bp_status = bpStatus
        if (bpStatus !== 'normal') { if (systolic) payload.systolic = parseInt(systolic); if (diastolic) payload.diastolic = parseInt(diastolic) }
      }
      if (has('Diabetes')) {
        payload.sugar_status = sugarStatus
        if (sugarStatus !== 'normal') { if (fastingSugar) payload.fasting_sugar = parseFloat(fastingSugar); if (postMealSugar) payload.post_meal_sugar = parseFloat(postMealSugar) }
      }
      if (has('Thyroid'))  payload.thyroid_type   = thyroidType
      if (has('PCOS') && pcosDiagnosed !== null) payload.pcos_diagnosed = pcosDiagnosed
      if (has('PCOD') && pcodDiagnosed !== null) payload.pcod_diagnosed = pcodDiagnosed
      if (has('Appendicitis'))              payload.appendicitis_phase = appendicitisPhase
      if (has('Other') && otherCondition.trim()) payload.other_condition = otherCondition.trim()
      if (statuses.includes('Other') && otherStatus.trim()) payload.other_status = otherStatus.trim()

      await updateHealthProfile(payload)
      toast.success('Health profile updated!')
      navigate('/dashboard')
    } catch (err) { toast.error(err.message || 'Failed to update') }
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
        <div className="flex gap-2 bg-gray-100 p-1.5 rounded-2xl mb-6">
          <TabButton active={tab === 'profile'} onClick={() => setTab('profile')} icon={User}       label="Profile" />
          <TabButton active={tab === 'health'}  onClick={() => setTab('health')}  icon={HeartPulse} label="Health" />
          <TabButton active={tab === 'status'}  onClick={() => setTab('status')}  icon={Activity}   label="Status" />
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">

          {/* Profile Tab */}
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

          {/* Health Tab */}
          {tab === 'health' && (
            <div className="space-y-5">
              {userGender === 'male' && (
                <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  PCOS and PCOD are not applicable for male users.
                </div>
              )}
              <div>
                <p className="label mb-3">Health Conditions</p>
                <ChipToggle options={ALL_CONDITIONS} selected={conditions} onToggle={toggleCondition} disabledOptions={disabledForGender} />
              </div>

              {conditions.includes('Hypertension (BP)') && (
                <div className="bg-primary-50 rounded-xl p-4 border border-primary-100">
                  <p className="font-semibold text-primary-800 text-sm mb-3">Hypertension Details</p>
                  <RadioRow label="BP Status" options={['low', 'normal', 'high']} value={bpStatus} onChange={handleBpStatusChange} />
                  {bpStatus !== 'normal' && (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-semibold text-gray-600 block mb-1">Systolic (mmHg) <span className="text-red-500">*</span></label>
                          <input type="number" className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${!systolic && bpError ? 'border-red-400' : 'border-primary-200'}`} placeholder={bpStatus === 'low' ? 'e.g. 80' : 'e.g. 130'} value={systolic} onChange={(e) => { setSystolic(e.target.value); setBpError(null) }} />
                        </div>
                        <div>
                          <label className="text-xs font-semibold text-gray-600 block mb-1">Diastolic (mmHg) <span className="text-red-500">*</span></label>
                          <input type="number" className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${!diastolic && bpError ? 'border-red-400' : 'border-primary-200'}`} placeholder={bpStatus === 'low' ? 'e.g. 50' : 'e.g. 90'} value={diastolic} onChange={(e) => { setDiastolic(e.target.value); setBpError(null) }} />
                        </div>
                      </div>
                      <ValidationError msg={bpError} />
                    </>
                  )}
                </div>
              )}
              {conditions.includes('Diabetes') && (
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                  <p className="font-semibold text-orange-800 text-sm mb-3">Diabetes Details</p>
                  <RadioRow label="Sugar Status" options={['low', 'normal', 'high']} value={sugarStatus} onChange={handleSugarStatusChange} />
                  {sugarStatus !== 'normal' && (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-semibold text-gray-600 block mb-1">Fasting Sugar <span className="text-red-500">*</span></label>
                          <input type="number" className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 ${!fastingSugar && sugarError ? 'border-red-400' : 'border-orange-200'}`} value={fastingSugar} onChange={(e) => { setFastingSugar(e.target.value); setSugarError(null) }} />
                        </div>
                        <div>
                          <label className="text-xs font-semibold text-gray-600 block mb-1">Post Meal Sugar <span className="text-red-500">*</span></label>
                          <input type="number" className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 ${!postMealSugar && sugarError ? 'border-red-400' : 'border-orange-200'}`} value={postMealSugar} onChange={(e) => { setPostMealSugar(e.target.value); setSugarError(null) }} />
                        </div>
                      </div>
                      <ValidationError msg={sugarError} />
                    </>
                  )}
                </div>
              )}
              {conditions.includes('Thyroid') && (
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="font-semibold text-blue-800 text-sm mb-3">Thyroid Type</p>
                  <RadioRow options={['hypothyroidism', 'hyperthyroidism']} value={thyroidType} onChange={setThyroidType} />
                </div>
              )}
              {conditions.includes('PCOS') && userGender !== 'male' && (
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="font-semibold text-purple-800 text-sm mb-3">PCOS — Diagnosed?</p>
                  <RadioRow options={['yes', 'no']} value={pcosDiagnosed === true ? 'yes' : pcosDiagnosed === false ? 'no' : ''} onChange={(v) => setPcosDiagnosed(v === 'yes')} />
                </div>
              )}
              {conditions.includes('PCOD') && userGender !== 'male' && (
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="font-semibold text-purple-800 text-sm mb-3">PCOD — Diagnosed?</p>
                  <RadioRow options={['yes', 'no']} value={pcodDiagnosed === true ? 'yes' : pcodDiagnosed === false ? 'no' : ''} onChange={(v) => setPcodDiagnosed(v === 'yes')} />
                </div>
              )}
              {conditions.includes('High Cholesterol') && (
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                  <p className="font-semibold text-orange-800 text-sm mb-2">High Cholesterol</p>
                  <p className="text-sm text-orange-700">Cholesterol-specific dietary analysis (AHA/WHO/ESC) will be included in your food scans.</p>
                </div>
              )}
              {conditions.includes('Appendicitis') && (
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="font-semibold text-blue-800 text-sm mb-3">Appendicitis Phase</p>
                  <RadioRow label="Select your current phase:" options={['acute', 'recovery']} value={appendicitisPhase} onChange={setAppendicitisPhase} />
                  <p className="text-xs text-blue-600 mt-1">{appendicitisPhase === 'acute' ? '⚠ Acute: Very strict restrictions.' : '✓ Recovery: Gradual return to normal diet.'}</p>
                </div>
              )}
              {conditions.includes('Other') && (
                <div className="bg-primary-50 rounded-xl p-4 border border-primary-100">
                  <p className="font-semibold text-primary-800 text-sm mb-2">Other Health Condition</p>
                  <p className="text-xs text-primary-600 mb-3">AI-powered dietary guidance for your condition.</p>
                  <label className="text-xs font-semibold text-gray-600 block mb-1">What is your health condition? <span className="text-red-500">*</span></label>
                  <input type="text" className="w-full px-3 py-2 rounded-xl border border-primary-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="e.g. Gout, GERD, Crohn's Disease, Fatty Liver" value={otherCondition} maxLength={100} onChange={(e) => setOtherCondition(e.target.value)} />
                  <p className="text-xs text-gray-400 mt-1">{otherCondition.length}/100</p>
                </div>
              )}
              <button onClick={saveHealth} disabled={saving} className="btn-primary w-full py-3">
                {saving ? <Spinner size="sm" /> : 'Save Health Conditions'}
              </button>
            </div>
          )}

          {/* Status Tab */}
          {tab === 'status' && (
            <div className="space-y-5">
              <div>
                <p className="label mb-3">Current Health Status</p>
                <p className="text-gray-400 text-sm mb-4">Temporary situations — pregnancy, illness, recovery, etc.</p>
                <ChipToggle options={STATUSES} selected={statuses} onToggle={toggleStatus} />
              </div>
              {statuses.includes('Other') && (
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <label className="text-xs font-semibold text-gray-600 block mb-2">Describe your current health status:</label>
                  <input type="text" className="w-full px-3 py-2 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="e.g. Pregnancy, Recovering from surgery, Post COVID" value={otherStatus} maxLength={100} onChange={(e) => setOtherStatus(e.target.value)} />
                </div>
              )}
              <button onClick={saveHealth} disabled={saving} className="btn-primary w-full py-3">
                {saving ? <Spinner size="sm" /> : 'Save Status'}
              </button>
            </div>
          )}
        </div>
        <button onClick={() => navigate('/dashboard')} className="btn-ghost w-full mt-4 text-center text-sm text-gray-500">
          ← Back to Dashboard
        </button>
      </div>
    </div>
  )
}
