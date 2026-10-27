// Dropdown for picking which regulator's rulebook to query.
// Currently only AE-Dubai exists; the backend returns whatever is in config.JURISDICTIONS.
// When CBN (Nigeria) is added later, this component needs zero changes.

export default function JurisdictionSelector({ options, value, onChange, disabled }) {
  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="jurisdiction"
        className="text-sm font-medium text-slate-600 hidden sm:inline"
      >
        Jurisdiction
      </label>
      <select
        id="jurisdiction"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || options.length === 0}
        className="
          text-sm rounded-lg border border-slate-300 bg-white
          px-3 py-1.5 pr-8 text-slate-700
          focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
          disabled:opacity-50 disabled:cursor-not-allowed
          cursor-pointer
        "
      >
        {options.length === 0 && <option value="">Loading…</option>}
        {options.map((opt) => (
          <option key={opt.code} value={opt.code}>
            {opt.regulator} — {opt.name}
          </option>
        ))}
      </select>
    </div>
  );
}