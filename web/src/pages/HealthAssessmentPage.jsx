import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitHealthProfile } from '../api/health'
import Spinner from '../components/Spinner'
import Navbar from '../components/Navbar'
import toast from 'react-hot-toast'
import { CheckCircle2 } from 'lucide-react'

const CONDITIONS = ['Hypertension (BP)', 'Diabetes', 'PCOS', 'PCOD', 'Thyroid', 'Heart Disease', 'Kidney Disease', 'Obesity', 'None']
const STATUSES   = ['Normal', 'Fever', 'Cold', 'Cough', 'Stomach Upset', 'Vomiting', 'Diarrhea', 'Weakness', 'Headache', 'Other']

function ChipSelector({ options, selected, onToggle, exclusive = false }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isSelected = selected.includes(opt)
        const isDisabled = exclusive && selected.includes('None') && opt !== 'None'
        return (
          <button
            key={opt}
            type="button"
            disabled={isDisabled}
            onClick={() => onToggle(opt)}
            className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-all duration-150 
              ${isSelected
                ? 'bg-primary-600 border-primary-600 text-white shadow-sm'
                : isDisabled
                  ? 'bg-gray-50 border-gray-200 text-gray-300 cursor-not-allowed'
                  : 'bg-white border-gray-200 text-gray-700 hover:border-primary-400 hover:text-primary-700'
              }`}
          >
            {isSelected && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />}
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function SubFormCard({ title, children }) {
  return (
    <div className="bg-primary-50 border border-primary-100 rounded-2xl p-5 mt-4">
      <h4 className="font-bold text-primary-800 mb-4">{title}</h4>
      {children}
    </div>
  )
}

function RadioGroup({ label, options, value, onChange }) {
  return (
    <div className="mb-3">
      <p className="text-sm font-semibold text-gray-700 mb-2">{label}</p>
      <div className="flex flex-wrap gap-3">
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer">
            <input type="radio" value={o} checked={value === o} onChange={() => onChange(o)}
              className="text-primary-600 focus:ring-primary-500" />
            <span className="text-sm text-gray-700 capitalize">{o}</span>
          </label>
        ))}
      </div>
    </div>
  )
}

export default function HealthAssessmentPage() {
  const navigate = useNavigate()
  const [conditions, setConditions] = useState([])
  const [statuses,   setStatuses]   = useState([])
  const [loading,    setLoading]    = useState(false)

  // Sub-form state
  const [bpStatus,    setBpStatus]    = useState('normal')
  const [systolic,    setSystolic]    = useState('')
  const [diastolic,   setDiastolic]   = useState('')
  const [sugarStatus, setSugarStatus] = useState('normal')
  const [fastingSugar, setFastingSugar] = useState('')
  const [postMealSugar, setPostMealSugar] = useState('')
  const [thyroidType, setThyroidType] = useState('hypothyroidism')
  const [pcosDiagnosed, setPcosDiagnosed] = useState(null)
  const [pcodDiagnosed, setPcodDiagnosed] = useState(null)

  const toggleCondition = (c) => {
    if (c === 'None') {
      setConditions(['None'])
      return
    }
    setConditions((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev.filter((x) => x !== 'None'), c]
    )
  }

  const toggleStatus = (s) =>
    setStatuses((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const has = (c) => conditions.includes(c)
      const payload = {
        hypertension:  has('Hypertension (BP)'),
        diabetes:      has('Diabetes'),
        thyroid:       has('Thyroid'),
        pcos:          has('PCOS'),
        pcod:          has('PCOD'),
        heart_disease: has('Heart Disease'),
        kidney_disease: has('Kidney Disease'),
        obesity:       has('Obesity'),
        none:          has('None'),
        current_health_statuses: statuses,
      }
      if (has('Hypertension (BP)')) {
        payload.bp_status = bpStatus
        if (systolic)  payload.systolic  = parseInt(systolic)
        if (diastolic) payload.diastolic = parseInt(diastolic)
      }
      if (has('Diabetes')) {
        payload.sugar_status = sugarStatus
        if (fastingSugar)  payload.fasting_sugar   = parseFloat(fastingSugar)
        if (postMealSugar) payload.post_meal_sugar  = parseFloat(postMealSugar)
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
          <p className="text-gray-500">Select your conditions. We'll generate your personalised food restrictions.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Conditions */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h2 className="font-bold text-gray-900 mb-1">Health Conditions</h2>
            <p className="text-gray-400 text-sm mb-4">Select all that apply</p>
            <ChipSelector options={CONDITIONS} selected={conditions} onToggle={toggleCondition} exclusive />

            {/* Hypertension sub-form */}
            {conditions.includes('Hypertension (BP)') && (
              <SubFormCard title="Hypertension Details">
                <RadioGroup label="BP Status" options={['normal', 'low', 'high']} value={bpStatus} onChange={setBpStatus} />
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <div>
                    <label className="label text-xs">Systolic (mmHg)</label>
                    <input className="input-field" type="number" placeholder="120" value={systolic} onChange={(e) => setSystolic(e.target.value)} />
                  </div>
                  <div>
                    <label className="label text-xs">Diastolic (mmHg)</label>
                    <input className="input-field" type="number" placeholder="80" value={diastolic} onChange={(e) => setDiastolic(e.target.value)} />
                  </div>
                </div>
              </SubFormCard>
            )}

            {/* Diabetes sub-form */}
            {conditions.includes('Diabetes') && (
              <SubFormCard title="Diabetes Details">
                <RadioGroup label="Sugar Status" options={['normal', 'low', 'high']} value={sugarStatus} onChange={setSugarStatus} />
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <div>
                    <label className="label text-xs">Fasting Sugar</label>
                    <input className="input-field" type="number" placeholder="90" value={fastingSugar} onChange={(e) => setFastingSugar(e.target.value)} />
                  </div>
                  <div>
                    <label className="label text-xs">Post Meal Sugar</label>
                    <input className="input-field" type="number" placeholder="140" value={postMealSugar} onChange={(e) => setPostMealSugar(e.target.value)} />
                  </div>
                </div>
              </SubFormCard>
            )}

            {/* Thyroid sub-form */}
            {conditions.includes('Thyroid') && (
              <SubFormCard title="Thyroid Details">
                <RadioGroup label="Thyroid Type" options={['hypothyroidism', 'hyperthyroidism']} value={thyroidType} onChange={setThyroidType} />
              </SubFormCard>
            )}

            {/* PCOS sub-form */}
            {conditions.includes('PCOS') && (
              <SubFormCard title="PCOS Details">
                <RadioGroup label="Diagnosed?" options={['yes', 'no']} value={pcosDiagnosed === true ? 'yes' : pcosDiagnosed === false ? 'no' : ''}
                  onChange={(v) => setPcosDiagnosed(v === 'yes')} />
              </SubFormCard>
            )}

            {/* PCOD sub-form */}
            {conditions.includes('PCOD') && (
              <SubFormCard title="PCOD Details">
                <RadioGroup label="Diagnosed?" options={['yes', 'no']} value={pcodDiagnosed === true ? 'yes' : pcodDiagnosed === false ? 'no' : ''}
                  onChange={(v) => setPcodDiagnosed(v === 'yes')} />
              </SubFormCard>
            )}
          </div>

          {/* Current health status */}
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
