import { Link } from 'react-router-dom'
import { Salad, ShieldCheck, Brain, ChartBar, ArrowRight, CheckCircle } from 'lucide-react'
import Navbar from '../components/Navbar'

const features = [
  { icon: ShieldCheck, title: 'Health Profiling',     desc: 'Track hypertension, diabetes, thyroid, PCOS/PCOD, heart & kidney conditions with detailed sub-profiles.' },
  { icon: ChartBar,    title: 'Smart BMI Tracker',    desc: 'Auto-calculate your BMI on registration and get categorized instantly — Underweight, Normal, Overweight, or Obese.' },
  { icon: Salad,       title: 'Food Restriction Engine', desc: 'Rule-based engine generates a personalized list of foods you should avoid based on your health conditions.' },
  { icon: Brain,       title: 'AI Scanner (Phase 2)', desc: 'Scan packaged food labels and live food images using AI — coming in Phase 2 with ML integration.' },
]

const steps = [
  { num: '01', title: 'Register & Set Profile',   desc: 'Enter your name, age, height, weight and food preference.' },
  { num: '02', title: 'Get Your BMI',              desc: 'BMI is calculated instantly and categorized for you.' },
  { num: '03', title: 'Health Assessment',         desc: 'Select your conditions and get a detailed health profile.' },
  { num: '04', title: 'See Your Restrictions',     desc: 'View a personalised list of foods to avoid on your dashboard.' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-white to-emerald-50 pt-20 pb-28">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
          <span className="inline-flex items-center gap-2 bg-primary-100 text-primary-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
            <Salad className="w-4 h-4" /> Phase 1 — Health Profiling System
          </span>
          <h1 className="text-4xl sm:text-6xl font-extrabold text-gray-900 leading-tight mb-6">
            Know What Food<br />
            <span className="text-primary-600">Suits Your Health</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            FoodHealth AI builds your complete health profile — BMI, conditions, restrictions — and soon scans food labels and live images with AI to keep you safe.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register" className="btn-primary text-base py-3 px-8">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/login" className="btn-outline text-base py-3 px-8">
              Sign In
            </Link>
          </div>
        </div>

        {/* Decorative blobs */}
        <div className="absolute -top-20 -right-20 w-96 h-96 bg-primary-100 rounded-full opacity-30 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-emerald-100 rounded-full opacity-40 blur-3xl pointer-events-none" />
      </section>

      {/* Features */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-3">Everything in One Place</h2>
            <p className="text-gray-500 text-lg max-w-xl mx-auto">A complete system to manage your dietary health, built for simplicity and scalability.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="p-6 rounded-2xl border border-gray-100 hover:border-primary-200 hover:shadow-md transition-all duration-200 group">
                <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center mb-4 group-hover:bg-primary-100 transition-colors">
                  <Icon className="w-6 h-6 text-primary-600" />
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 mb-3">How It Works</h2>
            <p className="text-gray-500 text-lg">Up and running in under 2 minutes.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s) => (
              <div key={s.num} className="bg-white rounded-2xl p-6 border border-gray-100 relative">
                <span className="text-5xl font-black text-primary-100 absolute top-4 right-4 leading-none">{s.num}</span>
                <h3 className="font-bold text-gray-900 mb-2 text-base">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-primary-600">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4">Start Your Health Journey Today</h2>
          <p className="text-primary-100 text-lg mb-8">Free to use. No credit card required.</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-white text-primary-700 font-bold px-8 py-3.5 rounded-xl hover:bg-primary-50 transition-colors text-base">
            Create Free Account <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-gray-900 text-center text-gray-400 text-sm">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Salad className="w-5 h-5 text-primary-500" />
          <span className="font-semibold text-white">FoodHealth AI</span>
        </div>
        <p>Phase 1 — AI Integration coming in Phase 2 · College Major Project</p>
      </footer>
    </div>
  )
}
