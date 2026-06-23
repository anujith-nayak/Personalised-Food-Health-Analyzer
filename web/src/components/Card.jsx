export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ icon: Icon, title, color = 'text-primary-600' }) {
  return (
    <div className="flex items-center gap-3 p-6 pb-4 border-b border-gray-50">
      {Icon && <div className={`p-2 rounded-xl bg-primary-50 ${color}`}><Icon className="w-5 h-5" /></div>}
      <h3 className="font-bold text-gray-900 text-base">{title}</h3>
    </div>
  )
}
