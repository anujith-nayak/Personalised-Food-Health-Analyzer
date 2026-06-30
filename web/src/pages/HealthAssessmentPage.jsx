import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitHealthProfile, getProfile } from '../api/health'
import Spinner from '../components/Spinner'
import Navbar from '../components/Navbar'
import toast from 'react-hot-toast'
import { CheckCircle2, AlertCircle } from 'lucide-react'

// Conditions that only apply to female / other
const FEMALE_ONLY = ['PCOS', 'PCOD']

const ALL_CONDITIONS = [
  'Hypertension (BP)', 'Diabetes', 'PCOS', 'PCOD',
  'Thyroid', 'Heart Disease', 'Kidney Disease', 'Obesity', 'None',
]
const STATUSES = [
  'Normal', 'Fever', 'Cold', 'Cough', 'Stomach Upset',
  'Vomiting', 'Diarrhea', 'Weakness', 'Headache', 'Other',
]

// BP validation ranges
const BP_RANGES = {
  low:    { systolic: [0, 89],   diastolic: [0, 59] },
  normal: null, // no input needed
  high:   { systolic: [121, 300], diastolic: [81, 200] },
}
// Sugar validation ranges
const SUGAR_RANGES = {
  low:    { fasting: [0, 69],    post_meal: [0, 79] },
  normal: null,
  high:   { fasting: [100, 600], post_meal: [140, 600] },
}

function validateBP(status, systolic, diastolic) {
  if (status === 'normal' || !BP_RANGES[status]) return null
  const r = BP_RANGES[status]
  if (systolic) {
    const [lo, hi] = r.systolic
    if (systolic < lo || systolic > hi)
      return `Systolic ${systolic} mmHg doesn't match "${status}" BP range (${lo}–${hi} mmHg). Change the value or select a different status.`
  }
  if (diastolic) {
    const [lo, hi] = r.diastolic
    if (diastolic < lo || diastolic > hi)
      return `Diastolic ${diastolic} mmHg doesn't match "${status}" BP range (${lo}–${hi} mmHg). Change the value or select a different status.`
  }
  return null
}

function validateSugar(status, fasting, postMeal) {
  if (status === 'normal' || !SUGAR_RANGES[status]) return null
  const r = SUGAR_RANGES[status]
  if (fasting) {
    const [lo, hi] = r.fasting
    if (fasting < lo || fasting > hi)
      return `Fasting sugar ${fasting} doesn't match "${status}" range (${lo}–${hi}). Change the value or select a different status.`
  }
  if (postMeal) {
    const [lo, hi] = r.post_meal
    if (postMeal < lo || postMeal > hi)
      return `Post-meal sugar ${postMeal} doesn't match "${status}" range (${lo}–${hi}). Change the value or select a different status.`
  }
  return null
}

function ChipSelector({ options, selected, onToggle, disabledOptions = [] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isSel       = selected.includes(opt)
        // Block other chips when None is active, but NEVER block None itself
        const isNoneBlock = selected.includes('None') && opt !== 'None'
        const isDisabled  = disabledOptions.includes(opt) || isNoneBlock
        return (
          <button
            key={opt}
            type="button"
            disabled={isDisabled}
            onClick={() => onToggle(opt)}
            title={disabledOptions.includes(opt) ? 'Not applicable for your gender' : undefined}
            className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-all duration-150
              ${isSel
                ? 'bg-primary-600 border-primary-600 text-white shadow-sm'
                : isDisabled
                  ? 'bg-gray-50 border-gray-200 text-gray-300 cursor-not-allowed'
                  : 'bg-white border-gray-200 text-gray-700 hover:border-primary-400 hover:text-primary-700'
              }`}
          >
            {isSel && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />}
            {opt}
            {disabledOptions.includes(opt) && <span className="ml-1 text-xs">(N/A)</span>}
          </button>
        )
      })}
    </div>
  )
}

function SubCard({ title, color = 'primary', children }) {
  const styles = {
    primary: 'bg-primary-50 border-primary-100 text-primary-800',
    orange:  'bg-orange-50 border-orange-100 text-orange-800',
    blue:    'bg-blue-50 border-blue-100 text-blue-800',
    purple:  'bg-purple-50 border-purple-100 text-purple-800',
  }
  return (
    <div className={`border rounded-2xl p-5 mt-4 ${styles[color]}`}>
      <p className="font-bold text-sm mb-4">{title}</p>
      {children}
    </div>
  )
}

function RadioGroup({ label, options, value, onChange }) {
  return (
    <div className="mb-3">
      {label && <p className="text-sm font-semibold mb-2">{label}</p>}
      <div className="flex flex-wrap gap-4">
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer text-sm capitalize">
            <input type="radio" value={o} checked={value === o} onChange={() => onChange(o)}
              className="accent-primary-600" />
            {o}
          </label>
        ))}
      </div>
    </div>
  )
}

function ValidationError({ msg }) {
  if (!msg) return null
  return (
    <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mt-3">
      <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
      <p className="text-red-700 text-sm">{msg}</p>
    </div>
  )
}

export default function HealthAssessmentPage() {
  const navigate = useNavigate()
  const [userGender, setUserGender] = useState(null)
  const [conditions, setConditions] = useState([])
  const [statuses,   setStatuses]   = useState([])
  const [loading,    setLoading]    = useState(false)

  // Hypertension
  const [bpStatus,  setBpStatus]  = useState('normal')
  const [systolic,  setSystolic]  = useState('')
  const [diastolic, setDiastolic] = useState('')
  const [bpError,   setBpError]   = useState(null)

  // Diabetes
  const [sugarStatus,   setSugarStatus]   = useState('normal')
  const [fastingSugar,  setFastingSugar]  = useState('')
  const [postMealSugar, setPostMealSugar] = useState('')
  const [sugarError,    setSugarError]    = useState(null)

  // Thyroid
  const [thyroidType, setThyroidType] = useState('hypothyroidism')

  // PCOS/PCOD
  const [pcosDiagnosed, setPcosDiagnosed] = useState(null)
  const [pcodDiagnosed, setPcodDiagnosed] = useState(null)

  // Load user gender to conditionally hide PCOS/PCOD
  useEffect(() => {
    getProfile().then((r) => setUserGender(r.data.gender)).catch(() => {})
  }, [])

  // Conditions disabled for males
  const disabledForGender = userGender === 'male' ? FEMALE_ONLY : []

  const toggleCondition = (c) => {
    if (disabledForGender.includes(c)) return
    if (c === 'None') {
      // Toggle None — if already selected, deselect it (re-enables all others)
      setConditions((p) => p.includes('None') ? [] : ['None'])
      return
    }
    setConditions((p) =>
      p.includes(c) ? p.filter((x) => x !== c) : [...p.filter((x) => x !== 'None'), c]
    )
  }
  const toggleStatus = (s) =>
    setStatuses((p) => p.includes(s) ? p.filter((x) => x !== s) : [...p, s])

  // Real-time validation
  const handleBpStatusChange = (v) => {
    setBpStatus(v)
    setBpError(null)
    setSystolic('')
    setDiastolic('')
  }
  const handleSugarStatusChange = (v) => {
    setSugarStatus(v)
    setSugarError(null)
    setFastingSugar('')
    setPostMealSugar('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Client-side validation before submit
    let valid = true
    if (conditions.includes('Hypertension (BP)') && bpStatus !== 'normal') {
      if (!systolic) { setBpError('Systolic value is required for ' + bpStatus + ' BP'); valid = false }
      else if (!diastolic) { setBpError('Diastolic value is required for ' + bpStatus + ' BP'); valid = false }
      else {
        const err = validateBP(bpStatus, parseInt(systolic), parseInt(diastolic))
        if (err) { setBpError(err); valid = false }
      }
    }
    if (conditions.includes('Diabetes') && sugarStatus !== 'normal') {
      if (!fastingSugar) { setSugarError('Fasting sugar value is required for ' + sugarStatus + ' sugar'); valid = false }
      else if (!postMealSugar) { setSugarError('Post meal sugar value is required for ' + sugarStatus + ' sugar'); valid = false }
      else {
        const err = validateSugar(sugarStatus, parseFloat(fastingSugar), parseFloat(postMealSugar))
        if (err) { setSugarError(err); valid = false }
      }
    }
    if (!valid) { toast.error('Please fill in the required values'); return }

    setLoading(true)
    try {
      const has = (c) => conditions.includes(c)
      const payload = {
        hypertension:   has('Hypertension (BP)'),
        diabetes:       has('Diabetes'),
        thyroid:        has('Thyroid'),
        pcos:           has('PCOS'),
        pcod:           has('PCOD'),
        heart_disease:  has('Heart Disease'),
        kidney_disease: has('Kidney Disease'),
        obesity:        has('Obesity'),
        none:           has('None'),
        current_health_statuses: statuses,
      }
      if (has('Hypertension (BP)')) {
        payload.bp_status = bpStatus
        if (bpStatus !== 'normal') {
          if (systolic)  payload.systolic  = parseInt(systolic)
          if (diastolic) payload.diastolic = parseInt(diastolic)
        }
      }
      if (has('Diabetes')) {
        payload.sugar_status = sugarStatus
        if (sugarStatus !== 'normal') {
          if (fastingSugar)  payload.fasting_sugar   = parseFloat(fastingSugar)
          if (postMealSugar) payload.post_meal_sugar  = parseFloat(postMealSugar)
        }
      }
      if (has('Thyroid')) payload.thyroid_type = thyroidType
      if (has('PCOS') && pcosDiagnosed !== null) payload.pcos_diagnosed = pcosDiagnosed
      if (has('PCOD') && pcodDiagnosed !== null) payload.pcod_diagnosed = pcodDiagnosed

      await submitHealthProfile(payload)
      toast.success('Health profile saved!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.message || 'Failed to save')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Health Assessment</h1>
          <p className="text-gray-500">Select your conditions — we'll personalise your food restrictions.</p>
          {userGender === 'male' && (
            <div className="mt-3 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              PCOS and PCOD are not applicable for male users and have been disabled.
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ── Condition selection ─────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h2 className="font-bold text-gray-900 mb-1">Health Conditions</h2>
            <p className="text-gray-400 text-sm mb-4">Select all that apply</p>
            <ChipSelector
              options={ALL_CONDITIONS}
              selected={conditions}
              onToggle={toggleCondition}
              disabledOptions={disabledForGender}
            />

            {/* Hypertension sub-form */}
            {conditions.includes('Hypertension (BP)') && (
              <SubCard title="Hypertension Details" color="primary">
                <RadioGroup
                  label="BP Status"
                  options={['low', 'normal', 'high']}
                  value={bpStatus}
                  onChange={handleBpStatusChange}
                />
                {bpStatus === 'normal' && (
                  <p className="text-sm text-primary-600 bg-primary-100 rounded-lg px-3 py-2">
                    ✓ Normal BP — no food restrictions applied.
                  </p>
                )}
                {bpStatus !== 'normal' && (
                  <>
                    <p className="text-xs text-gray-500 mb-2">
                      Enter your reading — <span className="text-red-500 font-semibold">required</span> to apply correct restrictions:
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-gray-600 block mb-1">Systolic (mmHg) <span className="text-red-500">*</span></label>
                        <input className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${!systolic && bpError ? 'border-red-400' : 'border-primary-200'}`}
                          type="number" placeholder={bpStatus === 'low' ? 'e.g. 80' : 'e.g. 130'}
                          value={systolic}
                          onChange={(e) => { setSystolic(e.target.value); setBpError(null) }} />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-gray-600 block mb-1">Diastolic (mmHg) <span className="text-red-500">*</span></label>
                        <input className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${!diastolic && bpError ? 'border-red-400' : 'border-primary-200'}`}
                          type="number" placeholder={bpStatus === 'low' ? 'e.g. 50' : 'e.g. 90'}
                          value={diastolic}
                          onChange={(e) => { setDiastolic(e.target.value); setBpError(null) }} />
                      </div>
                    </div>
                    <ValidationError msg={bpError} />
                  </>
                )}
              </SubCard>
            )}

            {/* Diabetes sub-form */}
            {conditions.includes('Diabetes') && (
              <SubCard title="Diabetes Details" color="orange">
                <RadioGroup
                  label="Sugar Status"
                  options={['low', 'normal', 'high']}
                  value={sugarStatus}
                  onChange={handleSugarStatusChange}
                />
                {sugarStatus === 'normal' && (
                  <p className="text-sm text-orange-700 bg-orange-100 rounded-lg px-3 py-2">
                    ✓ Normal sugar — no sugar-related restrictions applied.
                  </p>
                )}
                {sugarStatus !== 'normal' && (
                  <>
                    <p className="text-xs text-gray-500 mb-2">Enter your reading — <span className="text-red-500 font-semibold">required</span> to apply correct restrictions:</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-gray-600 block mb-1">Fasting Sugar <span className="text-red-500">*</span></label>
                        <input className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 ${!fastingSugar && sugarError ? 'border-red-400' : 'border-orange-200'}`}
                          type="number" placeholder={sugarStatus === 'low' ? 'e.g. 60' : 'e.g. 110'}
                          value={fastingSugar}
                          onChange={(e) => { setFastingSugar(e.target.value); setSugarError(null) }} />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-gray-600 block mb-1">Post Meal Sugar <span className="text-red-500">*</span></label>
                        <input className={`w-full px-3 py-2 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 ${!postMealSugar && sugarError ? 'border-red-400' : 'border-orange-200'}`}
                          type="number" placeholder={sugarStatus === 'low' ? 'e.g. 70' : 'e.g. 160'}
                          value={postMealSugar}
                          onChange={(e) => { setPostMealSugar(e.target.value); setSugarError(null) }} />
                      </div>
                    </div>
                    <ValidationError msg={sugarError} />
                  </>
                )}
              </SubCard>
            )}

            {/* Thyroid sub-form */}
            {conditions.includes('Thyroid') && (
              <SubCard title="Thyroid Type" color="blue">
                <RadioGroup options={['hypothyroidism', 'hyperthyroidism']} value={thyroidType} onChange={setThyroidType} />
              </SubCard>
            )}

            {/* PCOS sub-form */}
            {conditions.includes('PCOS') && (
              <SubCard title="PCOS — Have you been diagnosed?" color="purple">
                <RadioGroup
                  options={['yes', 'no']}
                  value={pcosDiagnosed === true ? 'yes' : pcosDiagnosed === false ? 'no' : ''}
                  onChange={(v) => setPcosDiagnosed(v === 'yes')}
                />
              </SubCard>
            )}

            {/* PCOD sub-form */}
            {conditions.includes('PCOD') && (
              <SubCard title="PCOD — Have you been diagnosed?" color="purple">
                <RadioGroup
                  options={['yes', 'no']}
                  value={pcodDiagnosed === true ? 'yes' : pcodDiagnosed === false ? 'no' : ''}
                  onChange={(v) => setPcodDiagnosed(v === 'yes')}
                />
              </SubCard>
            )}
          </div>

          {/* ── Current health status ───────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h2 className="font-bold text-gray-900 mb-1">Current Health Status</h2>
            <p className="text-gray-400 text-sm mb-4">How are you feeling right now?</p>
            <ChipSelector options={STATUSES} selected={statuses} onToggle={toggleStatus} />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3.5 text-base">
            {loading ? <Spinner size="sm" /> : 'Save & Go to Dashboard →'}
          </button>
        </form>
      </div>
    </div>
  )
}
