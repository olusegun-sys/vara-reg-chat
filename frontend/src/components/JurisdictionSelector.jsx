import { useState, useEffect, useRef } from "react";

export default function JurisdictionSelector({ options, value, onChange, disabled, isSending }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close the menu if the user clicks outside of it
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [isOpen]);

  const selectedOption = options.find((opt) => opt.code === value);

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          flex items-center justify-between gap-2
          bg-luxury border border-slate-700 text-slate-200 
          text-xs font-medium rounded-full px-3 py-1.5
          focus:outline-none focus:ring-2 focus:ring-brand-500
          disabled:opacity-50 disabled:cursor-not-allowed transition-colors
          hover:bg-slate-800 min-w-[140px]
        `}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {isSending ? (
          <span className="flex items-center gap-2 text-slate-400">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Searching...
          </span>
        ) : selectedOption ? (
          <span className="flex items-center gap-1.5 truncate">
            <span className="font-semibold text-white">{selectedOption.regulator}</span>
            <span className="text-slate-500">({selectedOption.code})</span>
          </span>
        ) : (
          <span className="text-slate-400">Loading…</span>
        )}
        
        {/* Chevron Icon */}
        <svg className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 top-[calc(100%+8px)] w-[240px] bg-[#12141B] border border-slate-700 rounded-xl shadow-xl z-50 py-1.5 animate-fade-in origin-top-right">
          {options.length === 0 ? (
            <div className="px-4 py-2 text-xs text-slate-400">Loading...</div>
          ) : (
            options.map((opt) => {
              const isSelected = opt.code === value;
              return (
                <button
                  key={opt.code}
                  type="button"
                  onClick={() => {
                    onChange(opt.code);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-4 py-2.5 text-sm text-left transition-colors
                    ${isSelected ? "bg-slate-800/60 text-white" : "text-slate-300 hover:bg-slate-800/40 hover:text-white"}
                  `}
                >
                  <div className="flex flex-col min-w-0 pr-2">
                    <span className="font-medium truncate">{opt.regulator}</span>
                    <span className="text-[10px] text-slate-500 truncate">{opt.name}</span>
                  </div>
                  
                  {/* Check icon for selected state */}
                  {isSelected && (
                    <svg className="w-4 h-4 text-brand-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                  )}
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}