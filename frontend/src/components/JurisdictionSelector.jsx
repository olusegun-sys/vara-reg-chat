export default function JurisdictionSelector({ options, value, onChange, disabled }) {
  return (
    <div className="relative flex items-center">
      <select
        id="jurisdiction"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || options.length === 0}
        className="
          appearance-none bg-luxury border border-slate-700 text-slate-200 
          text-xs font-medium rounded-full px-3 py-1.5 pr-8
          focus:outline-none focus:ring-2 focus:ring-brand-500
          disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer
          max-w-[160px] truncate shadow-sm
        "
      >
        {options.length === 0 && <option value="">Loading…</option>}
        {options.map((opt) => (
          <option key={opt.code} value={opt.code}>
            {opt.regulator} ({opt.code})
          </option>
        ))}
      </select>
      
      {/* Custom chevron icon to replace the native select arrow */}
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
        </svg>
      </div>
    </div>
  );
}