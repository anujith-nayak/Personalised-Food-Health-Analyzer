import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  uploadBloodReport,
  getBloodReport,
  confirmBloodReport,
  deleteBloodReport,
} from '../api/bloodReport'
import Navbar from '../components/Navbar'
import Spinner from '../components/Spinner'
import BloodBiomarkerAnalysis from '../components/BloodBiomarkerAnalysis'
import toast from 'react-hot-toast'

import {
  FileText, Upload, CheckCircle2, AlertTriangle, ArrowRight,
  Trash2, Edit3, ShieldCheck, ArrowLeft, RefreshCw, X, Plus
} from 'lucide-react'

export default function BloodReportPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const [report, setReport] = useState(null)
  const [editableResults, setEditableResults] = useState([])
  const [error, setError] = useState(null)

  // Fetch active blood report on mount
  useEffect(() => {
    fetchReport()
  }, [])

  const normalizeResultItems = (items) => {
    return (items || []).map((item) => ({
      parameter_key: item.parameter_key || item.key || `param_${Math.random()}`,
      display_name: item.display_name || item.name || item.parameter_key || 'Unknown Parameter',
      value: item.value ?? item.val ?? '',
      unit: item.unit || '',
      reference_range: item.reference_range || item.normal_range || '—',
      status: item.status || 'Review',
    }))
  }

  const fetchReport = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getBloodReport()
      if (res.data?.has_report && res.data.report) {
        setReport(res.data.report)
        setEditableResults(normalizeResultItems(res.data.report.results))
      } else {
        setReport(null)
        setEditableResults([])
      }
    } catch (e) {
      console.error('Failed to fetch blood report:', e)
    } finally {
      setLoading(false)
    }
  }

  // Handle file upload
  const handleFileUpload = async (file) => {
    if (!file) return

    const allowed = ['pdf', 'jpg', 'jpeg', 'png']
    const ext = file.name.split('.').pop().toLowerCase()
    if (!allowed.includes(ext)) {
      setError('Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG file.')
      toast.error('Please upload a PDF or Image file.')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('File size is too large. Maximum 10MB allowed.')
      toast.error('File size exceeds 10MB limit.')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const res = await uploadBloodReport(file)
      toast.success('Report uploaded successfully!')
      setReport(res.data)
      setEditableResults(normalizeResultItems(res.data.results))
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to process blood report.'
      setError(msg)
      toast.error(msg)
    } finally {
      setUploading(false)
    }
  }

  // Handle editing cell values
  const handleValueChange = (index, field, newValue) => {
    const updated = [...editableResults]
    updated[index][field] = newValue
    setEditableResults(updated)
  }

  // Add custom parameter row
  const handleAddRow = () => {
    setEditableResults([
      ...editableResults,
      {
        parameter_key: 'custom_' + Date.now(),
        display_name: 'Custom Parameter',
        value: 0,
        unit: 'mg/dL',
        reference_range: '',
        status: 'Review',
      },
    ])
  }

  // Delete row from review table
  const handleDeleteRow = (index) => {
    const updated = editableResults.filter((_, i) => i !== index)
    setEditableResults(updated)
  }

  // Confirm & save reviewed report parameters
  const handleConfirm = async () => {
    if (!report) return
    setConfirming(true)
    try {
      await confirmBloodReport(report.report_id, editableResults)
      toast.success('Blood report values confirmed and saved!')
      navigate('/dashboard')
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Confirmation failed.'
      toast.error(msg)
    } finally {
      setConfirming(false)
    }
  }

  // Delete whole report
  const handleDeleteReport = async () => {
    if (!report) return
    if (!window.confirm('Are you sure you want to delete this blood report?')) return

    try {
      await deleteBloodReport(report.report_id)
      toast.success('Blood report deleted.')
      setReport(null)
      setEditableResults([])
    } catch (err) {
      toast.error('Failed to delete blood report.')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Navigation back */}
        <button
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-1.5 text-gray-500 text-sm mb-4 hover:text-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>

        {/* ── Banner Section ───────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 font-semibold text-xs rounded-full mb-3">
                <ShieldCheck className="w-3.5 h-3.5" /> Enhance Your Health Profile — Optional
              </div>
              <h1 className="text-2xl font-extrabold text-gray-900">Upload Blood Test Report</h1>
              <p className="text-gray-500 text-sm mt-1.5 leading-relaxed">
                Upload your latest blood report to provide additional verified health parameters
                (e.g., HbA1c, Cholesterol, Glucose, Creatinine) for more personalized food health analysis.
              </p>
            </div>
            <FileText className="w-12 h-12 text-primary-500 flex-shrink-0 opacity-80" />
          </div>

          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>
              <strong>100% Optional:</strong> You can use FoodHealth AI fully without uploading a report.
              Your data is stored privately and is never used to diagnose medical conditions.
            </span>
          </div>
        </div>

        {/* ── Error Notification ───────────────────────────────────────────── */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
            <button onClick={() => setError(null)}>
              <X className="w-4 h-4 text-red-500 hover:text-red-700" />
            </button>
          </div>
        )}

        {/* ── Upload Area (Shown if no active report or re-uploading) ────────── */}
        {(!report || report.status === 'pending') && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf, .jpg, .jpeg, .png"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files[0])}
            />

            {!report && (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50/30 transition-all mb-6"
              >
                <div className="w-14 h-14 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Upload className="w-6 h-6" />
                </div>
                <p className="font-bold text-gray-900 text-base mb-1">
                  Click or drag blood report here
                </p>
                <p className="text-gray-400 text-xs">
                  Supported files: <strong>PDF, JPG, JPEG, PNG</strong> (Max 10MB)
                </p>
              </div>
            )}

            {uploading && (
              <div className="py-8 text-center">
                <Spinner size="lg" />
                <p className="font-semibold text-gray-700 text-sm mt-3">
                  Extracting medical parameters from report…
                </p>
              </div>
            )}

            {/* Action Buttons: Upload vs Skip */}
            {!uploading && !report && (
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-primary flex-1 py-3.5 text-sm font-bold flex items-center justify-center gap-2"
                >
                  <Upload className="w-4 h-4" /> Upload Blood Report
                </button>

                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-6 py-3.5 border border-gray-300 rounded-xl font-bold text-sm text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition-colors"
                >
                  Skip for now
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Extracted Information Review Table ───────────────────────────── */}
        {report && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
              <div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <p className="font-bold text-gray-900 text-base">Report Uploaded Successfully</p>
                </div>
                <p className="text-gray-400 text-xs mt-0.5">
                  File: <span className="font-medium text-gray-700">{report.file_name}</span> ·
                  Status: <span className="font-medium text-primary-600 capitalize">{report.status}</span>
                </p>
              </div>

              <button
                onClick={handleDeleteReport}
                className="text-xs text-red-600 hover:text-red-800 flex items-center gap-1 font-semibold"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete Report
              </button>
            </div>

            <div className="mb-4">
              <h2 className="font-bold text-gray-900 text-sm sm:text-base">Review Extracted Information</h2>
              <p className="text-gray-500 text-xs mt-1">
                Please review and adjust any extracted test values before confirming. Unconfirmed values will not be used in your health profile.
              </p>
            </div>

            {editableResults.length === 0 ? (
              <div className="p-6 bg-gray-50 rounded-xl text-center text-gray-500 text-xs mb-4">
                No test values automatically extracted from this report. Click "Add Parameter" to manually enter lab values.
              </div>
            ) : (
              <div className="overflow-x-auto mb-4 border border-gray-200 rounded-xl">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                    <tr>
                      <th className="py-2.5 px-3">Parameter</th>
                      <th className="py-2.5 px-3">Value</th>
                      <th className="py-2.5 px-3">Unit</th>
                      <th className="py-2.5 px-3">Ref. Range</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-2 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {editableResults.map((item, idx) => (
                      <tr key={idx} className="hover:bg-gray-50/50">
                        <td className="py-2.5 px-3 font-semibold text-gray-800 min-w-[220px]">
                          <input
                            type="text"
                            value={item.display_name}
                            onChange={(e) => handleValueChange(idx, 'display_name', e.target.value)}
                            className="w-full bg-transparent border-b border-transparent hover:border-gray-300 focus:border-primary-500 focus:outline-none px-1 py-0.5 whitespace-normal break-words"
                          />
                        </td>
                        <td className="py-2.5 px-3">
                          <input
                            type="number"
                            step="any"
                            value={item.value ?? ''}
                            onChange={(e) => handleValueChange(idx, 'value', e.target.value)}
                            className="w-24 font-bold bg-white border border-gray-300 rounded-lg px-2 py-1 text-gray-900 focus:ring-2 focus:ring-primary-400 focus:outline-none"
                          />
                        </td>
                        <td className="py-2.5 px-3">
                          <input
                            type="text"
                            value={item.unit || ''}
                            onChange={(e) => handleValueChange(idx, 'unit', e.target.value)}
                            className="w-20 bg-white border border-gray-300 rounded-lg px-2 py-1 text-xs text-gray-800 focus:ring-2 focus:ring-primary-400 focus:outline-none"
                          />
                        </td>
                        <td className="py-2.5 px-3 text-gray-600 text-xs font-medium whitespace-nowrap">
                          {item.reference_range || '—'}
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <span
                            className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${
                              item.status === 'Valid'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : item.status === 'Needs Review'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : 'bg-blue-50 text-blue-700 border-blue-200'
                            }`}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <button
                            onClick={() => handleDeleteRow(idx)}
                            className="text-gray-400 hover:text-red-600 p-1 rounded transition-colors"
                            title="Remove parameter"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <button
              onClick={handleAddRow}
              className="inline-flex items-center gap-1 text-xs text-primary-600 font-bold hover:text-primary-800 mb-6"
            >
              <Plus className="w-3.5 h-3.5" /> Add Lab Parameter
            </button>

            {/* Action Buttons: Confirm & Save vs Cancel */}
            <div className="flex flex-col sm:flex-row gap-3 pt-3 border-t border-gray-100">
              <button
                onClick={handleConfirm}
                disabled={confirming || editableResults.length === 0}
                className="btn-primary flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {confirming ? <Spinner size="sm" /> : <><CheckCircle2 className="w-4 h-4" /> Confirm & Save to Health Profile</>}
              </button>

              <button
                onClick={() => navigate('/dashboard')}
                className="px-6 py-3 border border-gray-300 rounded-xl font-bold text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Evidence-Based Knowledge Base Biomarker Analysis & Recommendations */}
        {report?.biomarker_analysis?.length > 0 && (
          <BloodBiomarkerAnalysis biomarkerAnalysis={report.biomarker_analysis} />
        )}
      </div>
    </div>
  )
}

