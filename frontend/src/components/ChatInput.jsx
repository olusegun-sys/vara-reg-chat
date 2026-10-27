import { useRef, useEffect } from "react";

export default function ChatInput({ value, onChange, onSend, disabled }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div className="p-3 sm:p-5 bg-luxury border-t border-slate-800/50">
      <div className="max-w-3xl mx-auto relative">
        <form 
          className="flex items-end gap-2 bg-luxury-light rounded-3xl p-2 border border-slate-700/50 focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500 transition-all shadow-lg"
          onSubmit={(e) => { e.preventDefault(); if (canSend) onSend(); }}
          noValidate
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message VARA Intelligence..."
            rows={1}
            disabled={disabled}
            className="
              flex-1 resize-none bg-transparent border-0
              px-4 py-3 text-[15px] text-white placeholder:text-slate-400
              focus:outline-none focus:ring-0
              disabled:opacity-50 disabled:cursor-not-allowed
              max-h-40 custom-scrollbar
            "
          />
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Send message"
            className="
              shrink-0 inline-flex items-center justify-center
              h-10 w-10 rounded-full bg-brand-600 text-white
              hover:bg-brand-500 active:scale-95
              focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-luxury-light
              disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-brand-600
              transition-all mb-1 mr-1
            "
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </form>
        <p className="text-center text-[11px] text-slate-500 mt-2">
          VARA Intelligence can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}