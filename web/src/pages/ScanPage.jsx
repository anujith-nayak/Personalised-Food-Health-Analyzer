import { useState } from 'react'
import Navbar from '../components/Navbar'
import { ScanLine, Camera, Rocket, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

function ScanCard({ icon: Icon, title, description, buttonLabel, badge }) {
  const [showModal, setShowModal] = useState(false)

  return (
    <>
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 flex flex-col">
        {/* Badge */}
        <div className="mb-6 flex justify-between items-start">
          <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center">
            <Icon className="w-8 h-8 text-primary-600" />
          </div>
          <span className="text-xs font-bold bg-amber-100 text-amber-700 px-3 py-1 rounded-full">
            {badge}
          </span>
        </div>

        <h3 className="text-xl font-extrabold text-gray-900 mb-3">{title}</h3>
        <p className="text-gray-500 text-sm leading-relaxed flex-1 mb-6">{description}</p>

        <button onClick={() => setShowModal(true)}
          className="btn-primary w-full py-3">
          <Icon className="w-4 h-4" /> {buttonLabel}
        </button>
      </div>

      {/* Coming soon modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full text-center animate-bounce-in">
            <div className="w-20 h-20 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Rocket className="w-10 h-10 text-primary-600" />
            </div>
            <h3 className="text-xl font-extrabold text-gray-900 mb-2">Coming in Phase 2</h3>
            <p className="text-gray-500 text-sm leading-relaxed mb-6">
              AI-powered food scanning with machine learning models will be integrated in Phase 2.
              OCR label scanning and live food recognition are in development.
            </p>
            <button onClick={() => setShowModal(false)} className="btn-primary w-full py-3">
              Got it!
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default function ScanPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-8">
          <Link to="/dashboard" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm mb-4">
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Food Scanner</h1>
          <p className="text-gray-500">AI-powered food analysis — powered by machine learning in Phase 2.</p>
        </div>

        {/* Phase 2 banner */}
        <div className="bg-gradient-to-r from-primary-600 to-emerald-600 rounded-2xl p-6 mb-8 text-white flex items-center gap-4">
          <Rocket className="w-10 h-10 flex-shrink-0 opacity-90" />
          <div>
            <p className="font-bold text-lg">Phase 2 Feature Preview</p>
            <p className="text-primary-100 text-sm mt-0.5">
              These features are ready for AI integration. The backend endpoints are already built — just waiting for ML models.
            </p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          <ScanCard
            icon={ScanLine}
            title="Scan Packaged Food Label"
            description="Point your camera at any packaged food label. Our AI will read the ingredients and nutrition information, then check them against your health profile to tell you if it's safe to eat."
            buttonLabel="Open Scanner"
            badge="Coming Phase 2"
          />
          <ScanCard
            icon={Camera}
            title="Live Food Scan"
            description="Take a photo of any meal or food item. Our computer vision model will identify the food and give you instant health recommendations based on your conditions and restrictions."
            buttonLabel="Open Camera"
            badge="Coming Phase 2"
          />
        </div>

        {/* How it will work */}
        <div className="mt-10 bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h2 className="font-bold text-gray-900 mb-4">How Phase 2 Will Work</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { step: '01', title: 'Scan or Capture',    desc: 'Use your camera to scan a label or photograph your meal.' },
              { step: '02', title: 'AI Analysis',         desc: 'ML model identifies ingredients, nutrition, and food type.' },
              { step: '03', title: 'Health Check',        desc: 'Results checked against your profile to flag unsafe items.' },
            ].map((s) => (
              <div key={s.step} className="relative p-4 bg-gray-50 rounded-xl">
                <span className="text-4xl font-black text-gray-100 absolute top-2 right-3">{s.step}</span>
                <p className="font-bold text-gray-900 text-sm mb-1">{s.title}</p>
                <p className="text-gray-500 text-xs leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
