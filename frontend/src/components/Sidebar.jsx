import { useState, useEffect } from "react";

// Delete confirmation modal — matches the app's near-black palette.
// Why a custom modal (not window.confirm): native browser confirm looks like
// an alert, not a professional app. Terry's clients will see this. This modal
// is styled, keyboard-accessible, and has an explicit destructive button.
function DeleteConfirmModal({ isOpen, onCancel, onConfirm, sessionTitle }) {
  // Close on Escape — the standard cancel gesture.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
    >
      <div
        className="w-full max-w-md bg-[#12141B] border border-slate-800 rounded-2xl shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/10 border border-red-500/30 mb-4 mx-auto">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-red-400">
            <path d="M3 6h18" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </div>

        <h2
          id="delete-modal-title"
          className="text-lg font-semibold text-white text-center mb-2"
        >
          Delete chat?
        </h2>

        {sessionTitle && (
          <p className="text-xs text-slate-500 text-center mb-3 truncate px-4">
            "{sessionTitle}"
          </p>
        )}

        <p className="text-sm text-slate-400 text-center leading-relaxed mb-6">
          This chat can't be recovered.
          <br />
          Share links from it will be disabled.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 px-4 rounded-lg text-sm font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            autoFocus
            className="flex-1 py-2.5 px-4 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-500 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-[#12141B]"
          >
            Delete chat
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar({ 
  sessions, 
  currentSessionId, 
  onSelectSession, 
  onNewChat,
  onRename,
  onDelete,
  onTogglePin,
  isOpen,
  onClose
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  // Which session is pending deletion confirmation (null = none).
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return 0; 
  });

  const handleEditSubmit = (id) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const sessionToDelete = deleteConfirmId
    ? sessions.find(s => s.id === deleteConfirmId)
    : null;

  const handleConfirmDelete = () => {
    if (deleteConfirmId) {
      onDelete(deleteConfirmId);
    }
    setDeleteConfirmId(null);
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden" 
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-luxury text-slate-300 flex flex-col h-full border-r border-slate-800 
        transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
        <div className="p-3">
          <button
            onClick={() => { onNewChat(); onClose(); }}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-brand-600 hover:bg-brand-500 transition-all text-sm font-medium text-white shadow-lg shadow-brand-900/50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 custom-scrollbar">
          {sortedSessions.map((session) => (
            <div key={session.id} className="relative group">
              {editingId === session.id ? (
                <input
                  type="text" autoFocus value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => handleEditSubmit(session.id)}
                  onKeyDown={(e) => e.key === "Enter" && handleEditSubmit(session.id)}
                  className="w-full text-sm bg-slate-800 text-white px-3 py-2 rounded-lg border border-slate-600 focus:outline-none"
                />
              ) : (
                <button
                  onClick={() => { onSelectSession(session.id); onClose(); }}
                  className={`w-full text-left pl-3 pr-8 py-2.5 rounded-lg text-sm truncate transition-all flex items-center gap-2 ${currentSessionId === session.id ? "bg-luxury-light text-white shadow-sm" : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200"}`}
                >
                  {session.is_pinned && (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 text-luxury-accent shrink-0 rotate-45">
                      <path d="M16 4a1 1 0 0 1 1 1v5l2 2v2H5v-2l2-2V5a1 1 0 0 1 1-1h8zM12 20a1 1 0 0 1-1-1v-2h2v2a1 1 0 0 1-1 1z" />
                    </svg>
                  )}
                  <span className="truncate">{session.title}</span>
                </button>
              )}

              {!editingId && (
                <div className="absolute right-1 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-1 bg-slate-800 rounded px-1 py-0.5 shadow-sm">
                  <button onClick={(e) => { e.stopPropagation(); onTogglePin(session.id); }} className="p-1 text-slate-400 hover:text-white" title={session.is_pinned ? "Unpin" : "Pin"}>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <line x1="12" y1="17" x2="12" y2="22" /><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.55V6a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4.55a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
                    </svg>
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); setEditingId(session.id); setEditTitle(session.title); }} className="p-1 text-slate-400 hover:text-white" title="Rename">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                    </svg>
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(session.id); }} className="p-1 text-slate-400 hover:text-red-400" title="Delete">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
        
        <div className="p-4 border-t border-slate-800/50 text-xs text-slate-500 text-center font-medium tracking-wide">
          VARA Intelligence
        </div>
      </div>

      {/* Delete confirmation modal — rendered outside the sidebar div so its
          overlay covers the full viewport, not just the sidebar column. */}
      <DeleteConfirmModal
        isOpen={deleteConfirmId !== null}
        onCancel={() => setDeleteConfirmId(null)}
        onConfirm={handleConfirmDelete}
        sessionTitle={sessionToDelete?.title}
      />
    </>
  );
}