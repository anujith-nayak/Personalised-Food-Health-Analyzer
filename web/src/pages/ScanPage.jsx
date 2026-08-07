import { useState, useRef, useCallback } from 'react'
import Navbar from '../components/Navbar'
import Spinner from '../components/Spinner'
import CameraCapture from '../components/CameraCapture'
import {
  ScanLine, Camera, Upload, Rocket, ArrowLeft,
  AlertTriangle, CheckCircle, RefreshCw, X, Image as ImageIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../api/client'

// ── Risk colour config ────────────────────────────────────────────────────────
const RISK_COLORS = {
  green:   { bg: 'bg-green-50',  border: 'border-green-300', text: 'text-green-700'  },
  yellow:  { bg: 'bg-yellow-50', border: 'border-yellow-300',text: 'text-yellow-700' },
  orange:  { bg: 'bg-orange-50', border: 'border-orange-300',text: 'text-orange-700' },
  red:     { bg: 'bg-red-50',    border: 'border-red-300',   text: 'text-red-700'    },
  darkred: { bg: 'bg-red-100',   border: 'border-red-500',   text: 'text-red-900'    },
  gray:    { bg: 'bg-gray-50',   border: 'border-gray-300',  text: 'text-gray-700'   },
}

// ── Compress image before upload (reduces processing time on mobile) ──────────
async function compressImage(file, maxWidthPx = 1600, quality = 0.85) {
  return new Promise((resolve) => {
    const img = new window.Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const scale = Math.min(1, maxWidthPx / img.width)
      const canvas = document.createElement('canvas')
      canvas.width  = img.width  * scale
      canvas.height = img.height * scale
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      canvas.toBlob(
        (blob) => resolve(new File([blob], file.name, { type: 'image/jpeg' })),
        'image/jpeg', quality
      )
    }
    img.src = url
  })
}

// ── Source picker modal ───────────────────────────────────────────────────────
function SourcePickerModal({ onCamera, onFiles, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50"
         onClick={onClose}>
      <div className="bg-white w-full sm:max-w-sm rounded-t-2xl sm:rounded-2xl p-6 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <p className="font-bold text-gray-900 text-lg mb-5 text-center">
          Choose Image Source
        </p>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <button onClick={onCamera}
            className="flex flex-col items-center gap-3 p-5 bg-primary-50 border-2 border-primary-200 rounded-2xl active:bg-primary-100 transition-colors">
            <Camera className="w-10 h-10 text-primary-600" />
            <span className="font-semibold text-primary-700 text-sm text-center">📷 Camera</span>
          </button>
          <button onClick={onFiles}
            className="flex flex-col items-center gap-3 p-5 bg-gray-50 border-2 border-gray-200 rounded-2xl active:bg-gray-100 transition-colors">
            <Upload className="w-10 h-10 text-gray-600" />
            <span className="font-semibold text-gray-700 text-sm text-center">📁 Gallery / Files</span>
          </button>
        </div>
        <button onClick={onClose}
          className="w-full py-3 text-gray-500 font-medium text-sm hover:text-gray-700">
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── Section wrapper for results ───────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5">
      <p className="font-bold text-gray-900 text-sm sm:text-base mb-3">{title}</p>
      {children}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ScanPage() {
  const [preview,     setPreview]     = useState(null)
  const [file,        setFile]        = useState(null)
  const [analyzing,   setAnalyzing]   = useState(false)
  const [result,      setResult]      = useState(null)
  const [error,       setError]       = useState(null)
  const [showPicker,  setShowPicker]  = useState(false)
  const [showCamera,  setShowCamera]  = useState(false)  // webcam modal
  const [aiResult,    setAiResult]    = useState(null)   // AI analysis for Other condition

  const fileInputRef = useRef(null)

  // ── Reset state ─────────────────────────────────────────────────────────
  const reset = useCallback(() => {
    setPreview(null)
    setFile(null)
    setResult(null)
    setError(null)
    setAiResult(null)
  }, [])

  // ── Handle file selection ────────────────────────────────────────────────
  const handleFile = useCallback(async (raw) => {
    if (!raw) return
    const compressed = await compressImage(raw)
    setFile(compressed)
    setPreview(URL.createObjectURL(compressed))
    setResult(null)
    setError(null)
    setShowPicker(false)
    setShowCamera(false)
  }, [])

  // ── Camera captured (from webcam modal) ───────────────────────────────────
  const handleCameraCapture = useCallback(async (capturedFile) => {
    setShowCamera(false)
    await handleFile(capturedFile)
  }, [handleFile])

  // ── Analyze ──────────────────────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!file) { setError('Please select or capture an image first.'); return }
    setAnalyzing(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/food/analyze-food-label', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
      setAiResult(null)

      // If the user has an "Other" condition, query AI for food-specific analysis
      try {
        const profileRes = await api.get('/health-profile')
        const otherCond  = profileRes.data?.other_condition
        if (otherCond) {
          const aiRes = await api.post('/ai-nutrition/query', {
            condition: otherCond,
            nutrition: res.data.nutrition_facts || {},
          })
          setAiResult(aiRes.data)
        }
      } catch (e) {
        // AI query is optional — don't fail the main scan result
        console.warn('AI nutrition query skipped:', e.message)
      }
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  const rc = result ? (RISK_COLORS[result.risk_color] || RISK_COLORS.gray) : null
  const healthScore = result?.health_score ?? null

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Source picker modal */}
      {showPicker && (
        <SourcePickerModal
          onCamera={() => { setShowPicker(false); setShowCamera(true) }}
          onFiles={() =>  { setShowPicker(false); fileInputRef.current?.click() }}
          onClose={() =>  setShowPicker(false)}
        />
      )}

      {/* Webcam modal */}
      {showCamera && (
        <CameraCapture
          onCapture={handleCameraCapture}
          onFallback={() => { setShowCamera(false); fileInputRef.current?.click() }}
          onClose={() => setShowCamera(false)}
        />
      )}

      {/* Hidden file input — gallery/files only */}
      <input ref={fileInputRef} type="file" accept="image/*"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])} />

      <div className="max-w-2xl mx-auto px-3 sm:px-6 py-6 sm:py-10">

        {/* Header */}
        <div className="mb-5">
          <Link to="/dashboard"
            className="inline-flex items-center gap-1.5 text-gray-500 text-sm mb-3 hover:text-gray-700">
            <ArrowLeft className="w-4 h-4" /> Dashboard
          </Link>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">Food Label Scanner</h1>
          <p className="text-gray-500 text-sm mt-1">
            Photograph or upload a nutrition label for a personalised health analysis.
          </p>
        </div>

        {/* ── Image selection panel ──────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-6 mb-4">

          {/* Image preview */}
          {preview ? (
            <div className="relative mb-4">
              <img src={preview} alt="Label preview"
                className="w-full max-h-72 object-contain rounded-xl border border-gray-100" />
              {!analyzing && (
                <button onClick={reset}
                  className="absolute top-2 right-2 bg-white/90 rounded-full p-1.5 shadow hover:bg-red-50">
                  <X className="w-4 h-4 text-gray-600" />
                </button>
              )}
            </div>
          ) : (
            <button onClick={() => setShowPicker(true)}
              className="w-full border-2 border-dashed border-gray-300 rounded-xl py-12
                         flex flex-col items-center gap-3 text-gray-400
                         hover:border-primary-400 hover:text-primary-500 active:bg-primary-50
                         transition-colors mb-4">
              <ImageIcon className="w-12 h-12" />
              <span className="font-medium text-sm">Tap to add a food label</span>
              <span className="text-xs">Camera · Gallery · Files</span>
            </button>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200
                            rounded-xl px-4 py-3 mb-4 text-sm text-red-700">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button onClick={handleAnalyze}
              disabled={analyzing || !file}
              className="flex-1 btn-primary py-3.5 text-base disabled:opacity-50
                         disabled:cursor-not-allowed min-h-[52px]">
              {analyzing
                ? <><Spinner size="sm" /><span className="ml-2">Analysing…</span></>
                : <><ScanLine className="w-5 h-5" /><span className="ml-1.5">Analyse Label</span></>
              }
            </button>

            {/* New Image button — always visible when image is selected */}
            {preview && !analyzing && (
              <button onClick={() => setShowPicker(true)}
                className="flex-shrink-0 flex items-center gap-2 px-4 py-3.5
                           border-2 border-gray-200 rounded-xl font-semibold text-sm
                           text-gray-700 hover:border-primary-400 hover:text-primary-700
                           active:bg-primary-50 transition-colors min-h-[52px]">
                <RefreshCw className="w-4 h-4" />
                <span className="hidden sm:inline">New Image</span>
              </button>
            )}
          </div>
        </div>

        {/* ── Tips card (shown when no result yet) ─────────────────────── */}
        {!result && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 mb-4">
            <p className="font-bold text-gray-900 text-sm mb-3">📸 Tips for best results</p>
            {[
              'Ensure the Nutrition Facts panel is fully visible',
              'Good lighting — avoid shadows on the label',
              'Hold the camera steady for a sharp image',
              'Use the rear camera for better quality',
            ].map((t) => (
              <div key={t} className="flex items-start gap-2 py-1">
                <CheckCircle className="w-3.5 h-3.5 text-primary-500 flex-shrink-0 mt-0.5" />
                <span className="text-gray-500 text-xs sm:text-sm">{t}</span>
              </div>
            ))}
          </div>
        )}

        {/* ── Results ──────────────────────────────────────────────────── */}
        {result && (
          <div className="space-y-4">

            {/* Health score card */}
            <div className={`${rc.bg} ${rc.border} border-2 rounded-2xl p-4 sm:p-5`}>
              <div className="flex items-center gap-4 mb-3">
                <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full flex flex-col
                                items-center justify-center text-white flex-shrink-0"
                  style={{ background:
                    result.risk_color === 'green'   ? '#16a34a' :
                    result.risk_color === 'yellow'  ? '#ca8a04' :
                    result.risk_color === 'orange'  ? '#ea580c' :
                    result.risk_color === 'darkred' ? '#991b1b' : '#dc2626'
                  }}>
                  <span className="font-black text-2xl sm:text-3xl leading-none">
                    {healthScore}
                  </span>
                  <span className="text-xs opacity-80">/100</span>
                </div>
                <div className="min-w-0">
                  <p className={`text-xl sm:text-2xl font-black ${rc.text}`}>
                    {result.risk_level}
                  </p>
                  <p className="text-gray-600 text-sm mt-0.5 leading-snug">
                    {result.risk_advice}
                  </p>
                  {result.user_conditions?.length > 0 && (
                    <p className="text-gray-400 text-xs mt-1 italic">
                      Based on: {result.user_conditions.slice(0, 3).join(', ')}
                    </p>
                  )}
                </div>
              </div>
              {/* Score bar */}
              <div className="w-full bg-white/60 rounded-full h-2.5">
                <div className="h-2.5 rounded-full transition-all"
                  style={{
                    width: `${healthScore}%`,
                    background:
                      result.risk_color === 'green'  ? '#16a34a' :
                      result.risk_color === 'yellow' ? '#ca8a04' :
                      result.risk_color === 'orange' ? '#ea580c' : '#dc2626'
                  }} />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0 — Dangerous</span><span>100 — Safe</span>
              </div>
            </div>

            {/* User health context */}
            {(result.user_bp || result.user_sugar || result.user_bmi) && (
              <div className="bg-primary-50 border border-primary-100 rounded-2xl p-4">
                <p className="font-semibold text-primary-800 text-sm mb-2">
                  Your Health Values Used
                </p>
                <div className="flex flex-wrap gap-4">
                  {result.user_bp && (
                    <div>
                      <p className="text-xs text-gray-500">Blood Pressure</p>
                      <p className="font-bold text-sm">{result.user_bp} mmHg</p>
                    </div>
                  )}
                  {result.user_sugar && (
                    <div>
                      <p className="text-xs text-gray-500">Fasting Sugar</p>
                      <p className="font-bold text-sm">{result.user_sugar} mg/dL</p>
                    </div>
                  )}
                  {result.user_bmi && (
                    <div>
                      <p className="text-xs text-gray-500">BMI</p>
                      <p className="font-bold text-sm">{parseFloat(result.user_bmi).toFixed(1)}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Critical allergen */}
            {result.has_critical_allergen && (
              <div className="bg-red-50 border-2 border-red-400 rounded-2xl p-4
                              flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-black text-red-700 text-sm">CRITICAL ALLERGEN</p>
                  <p className="text-red-600 text-sm mt-0.5">
                    {result.allergy_alerts?.filter(a => a.severity === 'Severe')
                      .map(a => a.allergen).join(', ')} — DO NOT consume.
                  </p>
                </div>
              </div>
            )}

            {/* STEP 1 — Extracted Nutrition Facts */}
            {result.nutrition_facts && Object.keys(result.nutrition_facts).length > 0 && (
              <Section title="① Extracted Nutrition Facts">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <tbody>
                      {Object.entries(result.nutrition_facts).map(([k, v]) => (
                        <tr key={k} className="border-b border-gray-50 last:border-0">
                          <td className="py-2 text-gray-500 capitalize pr-4">
                            {k.replace(/_/g, ' ')}
                          </td>
                          <td className="py-2 font-semibold text-right">
                            {v}{k === 'calories' ? ' kcal' :
                               k === 'sodium' || k === 'cholesterol' || k === 'potassium' ? ' mg' : ' g'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            )}

            {/* Ingredients */}
            {result.ingredients?.length > 0 && (
              <Section title="Detected Ingredients">
                <div className="flex flex-wrap gap-1.5">
                  {result.ingredients.map((i) => (
                    <span key={i} className="text-xs bg-gray-100 text-gray-700
                                             px-2.5 py-1 rounded-full">{i}</span>
                  ))}
                </div>
              </Section>
            )}

            {/* STEP 2 — Nutrient Evaluation */}
            {result.nutrient_evaluation?.length > 0 && (
              <Section title="② Nutrient Evaluation">
                <div className="space-y-2">
                  {result.nutrient_evaluation
                    .filter(e => e.status !== 'Not Available')
                    .map((e, i) => {
                      const colors = {
                        green:  'bg-green-100 text-green-800',
                        yellow: 'bg-yellow-100 text-yellow-800',
                        orange: 'bg-orange-100 text-orange-800',
                        red:    'bg-red-100 text-red-800',
                        gray:   'bg-gray-100 text-gray-600',
                        blue:   'bg-blue-100 text-blue-700',
                      }
                      const badge = colors[e.status_color] || colors.gray
                      return (
                        <div key={i} className="flex items-center justify-between
                                                 gap-3 py-1.5 border-b border-gray-50 last:border-0">
                          <div className="min-w-0">
                            <span className="text-sm font-medium text-gray-800">{e.nutrient}</span>
                            {e.value !== null && (
                              <span className="text-xs text-gray-400 ml-2">
                                {e.value}{e.unit}
                              </span>
                            )}
                            {e.note && (
                              <p className="text-xs text-gray-400 mt-0.5">{e.note}</p>
                            )}
                          </div>
                          <span className={`text-xs font-bold px-2.5 py-1 rounded-full
                                            flex-shrink-0 ${badge}`}>
                            {e.status}
                          </span>
                        </div>
                      )
                    })}
                </div>
              </Section>
            )}

            {/* STEP 3 — Disease Impact */}
            {result.disease_impact?.length > 0 && (
              <Section title="③ Disease-Specific Analysis">
                <div className="space-y-4">
                  {result.disease_impact.map((d, i) => {
                    const impactColors = {
                      green:  { bg: 'bg-green-50',  border: 'border-green-200',  text: 'text-green-700'  },
                      yellow: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700' },
                      orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' },
                      red:    { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700'    },
                      gray:   { bg: 'bg-gray-50',   border: 'border-gray-200',   text: 'text-gray-600'   },
                    }
                    const ic = impactColors[d.impact_color] || impactColors.gray
                    return (
                      <div key={i} className={`rounded-xl border p-3 ${ic.bg} ${ic.border}`}>
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-bold text-sm text-gray-900">{d.condition}</p>
                          <span className={`text-xs font-bold ${ic.text}`}>{d.overall_impact}</span>
                        </div>
                        {d.concerns.length > 0 && (
                          <div className="space-y-1 mb-2">
                            {d.concerns.map((c, ci) => (
                              <div key={ci} className="flex items-start gap-1.5 text-xs">
                                <AlertTriangle className="w-3 h-3 text-orange-500 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-700">{c.message}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {d.positives.length > 0 && (
                          <div className="space-y-1">
                            {d.positives.map((p, pi) => (
                              <div key={pi} className="flex items-start gap-1.5 text-xs">
                                <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-600">{p}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        <p className="text-xs text-gray-500 mt-2 italic">{d.summary}</p>
                      </div>
                    )
                  })}
                </div>
              </Section>
            )}

            {/* STEP 4 — Score Explanation */}
            {result.score_explanation?.length > 0 && (
              <Section title="④ How the Score Was Calculated">
                <div className="space-y-1">
                  {result.score_explanation.map((line, i) => (
                    <p key={i} className={`text-sm ${
                      line.startsWith('Final') ? 'font-bold text-gray-900 border-t border-gray-100 pt-2 mt-1'
                      : line.startsWith('Starting') ? 'font-semibold text-gray-700'
                      : 'text-gray-500'
                    }`}>
                      {line}
                    </p>
                  ))}
                </div>
              </Section>
            )}

            {/* STEP 5 — Final Recommendation */}
            {result.final_recommendation && (
              <div className={`${rc.bg} ${rc.border} border-2 rounded-2xl p-4`}>
                <p className={`font-bold text-sm mb-1 ${rc.text}`}>⑤ Final Recommendation</p>
                <p className="text-gray-800 text-sm leading-relaxed">
                  {result.final_recommendation}
                </p>
              </div>
            )}

            {/* AI Analysis — shown when user has an "Other" health condition */}
            {aiResult && (
              <div className="bg-blue-50 border-2 border-blue-200 rounded-2xl p-4 sm:p-5">
                <p className="font-bold text-blue-800 text-sm mb-1">
                  🤖 AI Analysis: {aiResult.condition}
                  {aiResult.source === 'rule_engine' && (
                    <span className="ml-2 text-xs font-normal text-blue-500">(Rule Engine)</span>
                  )}
                  {aiResult.source === 'ai_generated' && (
                    <span className="ml-2 text-xs font-normal text-purple-500">(AI Generated)</span>
                  )}
                </p>
                <p className="text-blue-700 text-sm leading-relaxed mb-3">{aiResult.summary}</p>

                {aiResult.foods_to_avoid?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold text-red-700 mb-1.5">⚠ Foods to Avoid:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {aiResult.foods_to_avoid.map((f, i) => (
                        <span key={i} className="text-xs bg-red-100 text-red-700 px-2.5 py-1 rounded-full">{f}</span>
                      ))}
                    </div>
                  </div>
                )}

                {aiResult.nutrients_to_limit?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold text-orange-700 mb-1.5">⚡ Nutrients to Limit:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {aiResult.nutrients_to_limit.map((n, i) => (
                        <span key={i} className="text-xs bg-orange-100 text-orange-700 px-2.5 py-1 rounded-full">{n}</span>
                      ))}
                    </div>
                  </div>
                )}

                {aiResult.foods_to_prefer?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold text-green-700 mb-1.5">✓ Recommended Foods:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {aiResult.foods_to_prefer.map((f, i) => (
                        <span key={i} className="text-xs bg-green-100 text-green-700 px-2.5 py-1 rounded-full">{f}</span>
                      ))}
                    </div>
                  </div>
                )}

                {aiResult.healthy_alternatives?.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold text-teal-700 mb-1">🥗 Healthier Alternatives:</p>
                    <ul className="space-y-0.5">
                      {aiResult.healthy_alternatives.map((a, i) => (
                        <li key={i} className="text-xs text-teal-800">• {a}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {aiResult.sample_meal && (
                  <div className="mt-2 p-3 bg-white rounded-xl border border-blue-100">
                    <p className="text-xs font-bold text-gray-700 mb-1">🍽 Sample Meal Plan:</p>
                    <p className="text-xs text-gray-600 leading-relaxed">{aiResult.sample_meal}</p>
                  </div>
                )}

                <p className="text-xs text-gray-400 mt-3 italic">{aiResult.medical_disclaimer}</p>
                <p className="text-xs text-blue-400 mt-1">
                  Source: {aiResult.guideline_source}
                </p>
              </div>
            )}

            {/* Allergy alerts */}
            {result.allergy_alerts?.filter(a => a.severity !== 'Severe').length > 0 && (
              <Section title="Allergy Warnings">
                <div className="space-y-2">
                  {result.allergy_alerts.map((a, i) => (
                    <div key={i} className={`rounded-xl p-3 border ${
                      a.severity === 'Moderate' ? 'border-orange-300 bg-orange-50' :
                      'border-yellow-300 bg-yellow-50'}`}>
                      <p className="font-bold text-sm">{a.allergen} — {a.severity}</p>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Contains: {a.matched_ingredient} · {a.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Alternatives */}
            {result.better_alternatives?.length > 0 && (
              <Section title="Better Alternatives">
                <div className="space-y-1.5">
                  {result.better_alternatives.map((a, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">{a}</span>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Serving advice */}
            {result.serving_advice?.length > 0 && (
              <Section title="Serving Advice">
                {result.serving_advice.map((a, i) => (
                  <p key={i} className="text-sm text-gray-700 py-0.5">• {a}</p>
                ))}
              </Section>
            )}

            {/* Upload Another */}
            <div className="pt-2 pb-8">
              <button onClick={() => setShowPicker(true)}
                className="w-full btn-outline py-4 text-base font-bold">
                <RefreshCw className="w-5 h-5" />
                Analyse Another Label
              </button>
            </div>
          </div>
        )}

        {/* Phase 2 teaser */}
        {!result && (
          <div className="bg-gradient-to-r from-primary-600 to-emerald-600
                          rounded-2xl p-4 sm:p-5 text-white flex items-center gap-3">
            <Rocket className="w-8 h-8 flex-shrink-0 opacity-90" />
            <div>
              <p className="font-bold text-sm">Live Food Scan — Phase 2</p>
              <p className="text-primary-100 text-xs mt-0.5">
                Point your camera at any food item for instant AI identification.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
