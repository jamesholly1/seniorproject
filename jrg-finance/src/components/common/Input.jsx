import './Input.css'

export default function Input({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  id,
  required,
  autoComplete,
  disabled,
}) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className={`input-group ${error ? 'input-group--error' : ''}`}>
      {label && (
        <label className="input-group__label" htmlFor={inputId}>
          {label}
          {required && <span className="input-group__required">*</span>}
        </label>
      )}
      <input
        id={inputId}
        type={type}
        className="input-group__field"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete={autoComplete}
        disabled={disabled}
      />
      {error && <p className="input-group__error">{error}</p>}
    </div>
  )
}
