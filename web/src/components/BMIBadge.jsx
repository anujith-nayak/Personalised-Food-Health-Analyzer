const config = {
  'Underweight':   { bg: 'bg-blue-100',   text: 'text-blue-700',   dot: 'bg-blue-500' },
  'Normal Weight': { bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500' },
  'Overweight':    { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' },
  'Obese':         { bg: 'bg-red-100',    text: 'text-red-700',    dot: 'bg-red-500' },
}

export default function BMIBadge({ category }) {
  const c = config[category] || { bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-400' }
  return (
    <span className={`chip ${c.bg} ${c.text} gap-1.5`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {category}
    </span>
  )
}
