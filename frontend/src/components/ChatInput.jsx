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
    <div className="flex items-end gap-2 p-3 bg-white border-t border-slate-200">
      {/* We wrap it in a form with onSubmit to catch Enter, but use noValidate to kill the red circle */}
      <form 
        className="flex-1 flex items-end gap-2"
        onSubmit={(e) => { e.preventDefault(); if (canSend) onSend(); }}
        noValidate
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the rulebook…"
          rows={1}
          disabled={disabled}
          className="
            flex-1 resize-none rounded-lg border border-slate-300 bg-white
            px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400
            focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
            disabled:opacity-50 disabled:cursor-not-allowed
            max-h-40
          "
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send message"
          className="
            shrink-0 inline-flex items-center justify-center
            h-10 w-10 rounded-lg bg-brand-600 text-white
            hover:bg-brand-700 active:bg-brand-900
            focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500
            disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-brand-600
            transition-colors
          "
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </button>
      </form>
    </div>
  );
}