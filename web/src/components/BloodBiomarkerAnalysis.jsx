import React from 'react'
import { Activity, ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react'

export default function BloodBiomarkerAnalysis({ biomarkerAnalysis = [] }) {
  if (!biomarkerAnalysis || biomarkerAnalysis.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-6 mb-6">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
        <Activity className="w-5 h-5 text-indigo-600" />
        <h3 className="text-lg font-bold text-gray-900">Blood Biomarker Analysis</h3>
        <span className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-2.5 py-0.5 rounded-full ml-auto">
          Evidence-Based KB
        </span>
      </div>

      <div className="space-y-4">
        {biomarkerAnalysis.map((item, index) => {
          const isHigh = item.condition === 'High'
          const isLow = item.condition === 'Low'
          const badgeColor = isHigh
            ? 'bg-red-50 text-red-700 border-red-200'
            : isLow
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : 'bg-blue-50 text-blue-700 border-blue-200'

          return (
            <div
              key={index}
              className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:shadow-xs transition-all"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h4 className="font-bold text-gray-900 text-base">{item.parameter}</h4>
                  {item.value && (
                    <p className="text-sm font-semibold text-gray-600 mt-0.5">{item.value}</p>
                  )}
                </div>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full border ${badgeColor}`}>
                  {item.condition}
                </span>
              </div>

              {item.recommendation && (
                <div className="mt-2.5 bg-white p-3 rounded-lg border border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-0.5">
                    Recommendation
                  </p>
                  <p className="text-sm font-bold text-gray-800 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                    {item.recommendation}
                  </p>
                  {item.reason && (
                    <p className="text-xs text-gray-600 mt-1 italic leading-relaxed">
                      "{item.reason}"
                    </p>
                  )}
                </div>
              )}

              {item.source && (
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
                  <div className="flex items-center gap-1 text-gray-600">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Source: <strong className="text-gray-800">{item.source}</strong> {item.organization && `(${item.organization})`}</span>
                  </div>
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-1"
                    >
                      Evidence <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
