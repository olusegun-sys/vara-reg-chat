
import { useEffect } from "react";

export default function SourceDrawer({ isOpen, onClose, sources }) {
  // Prevent background scrolling when drawer is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => { document.body.style.overflow = "unset"; };
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-[60] transition-opacity duration-300 ${
          isOpen ? "opacity-100 visible" : "opacity-0 invisible"
        }`}
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div
        className={`fixed inset-y-0 right-0 z-[70] w-full sm:w-[400px] bg-[#12141B] border-l border-slate-800 shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-slate-800 shrink-0">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Sources Referenced
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Source List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {sources && sources.length > 0 ? (
            sources.map((source, i) => (
              <a
                key={i}
                href={source.source_url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="block group bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 hover:border-brand-500/50 rounded-xl p-4 transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-slate-200 group-hover:text-white transition-colors leading-tight mb-1">
                      {source.document}
                      {source.section && source.section !== "General" && source.section !== "Web Search Result" && (
                        <span className="text-slate-400 font-normal"> ({source.section})</span>
                      )}
                    </h3>
                    
                    {source.authority_tier && (
                      <span className="inline-block text-[10px] font-semibold text-brand-400 uppercase tracking-wide mb-2 bg-brand-900/30 px-2 py-0.5 rounded-sm">
                        {source.authority_tier}
                      </span>
                    )}

                    {source.snippet && (
                      <p className="text-xs text-slate-400 italic leading-relaxed mt-2 line-clamp-4">
                        "{source.snippet}..."
                      </p>
                    )}
                    
                    <div className="flex items-center gap-1.5 mt-3 text-[11px] text-slate-500 group-hover:text-brand-400 transition-colors">
                      <span>Open Source</span>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </div>
                  </div>
                </div>
              </a>
            ))
          ) : (
            <div className="text-center text-slate-500 text-sm mt-10">
              No sources available for this message.
            </div>
          )}
        </div>
      </div>
    </>
  );
}