export function FormField({ label, error, children }) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

export function Input({ label, error, ...props }) {
  return (
    <FormField label={label} error={error}>
      <input className={`input-field ${error ? 'border-red-400 focus:ring-red-400' : ''}`} {...props} />
    </FormField>
  )
}

export function Select({ label, error, options, ...props }) {
  return (
    <FormField label={label} error={error}>
      <select className={`input-field ${error ? 'border-red-400' : ''}`} {...props}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </FormField>
  )
}
