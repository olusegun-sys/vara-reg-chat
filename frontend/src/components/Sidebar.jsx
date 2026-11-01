import { useState, useEffect, useRef } from "react"; // useRef added for click-outside detection

// Delete confirmation modal — matches the app's near-black palette.
// Why a custom modal (not window.confirm): native browser confirm looks like
// an alert, not a professional app. Terry's clients will see this. This modal
// is styled, keyboard-accessible, and has an explicit destructive button.
function DeleteConfirmModal({ isOpen, onCancel, onConfirm }) {
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
        <h2
          id="delete-modal-title"
          className="text-lg font-semibold text-white text-center mb-4"
        >
          Delete chat?
        </h2>

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
  const [editingId, setEditingId] = useState(null); // which session is being renamed (null = none)
  const [editTitle, setEditTitle] = useState(""); // the in-progress rename text
  // Which session's action menu is open (null = none). Single menu at a time.
  const [menuOpenId, setMenuOpenId] = useState(null);
  // Which session is pending deletion confirmation (null = none).
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  // Ref to the scrollable list container — used to detect clicks outside any menu.
  const menuContainerRef = useRef(null);

  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return 0; 
  });

  // Close the popover on any outside click or Escape press.
  // Why: on mobile there's no "hover off" — the user needs an explicit dismiss.
  // We listen at the document level so tapping anywhere closes the menu.
  useEffect(() => {
    if (menuOpenId === null) return; // nothing open — no listeners needed
    const onDocClick = (e) => {
      // If the click is inside the menu container, let the button handle it.
      // We use a data-attribute check so we don't have to track per-row refs.
      if (e.target.closest('[data-session-menu]')) return;
      setMenuOpenId(null);
    };
    const onEsc = (e) => {
      if (e.key === "Escape") setMenuOpenId(null);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("touchstart", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("touchstart", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, [menuOpenId]);

  const handleEditSubmit = (id) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim()); // persist the new title via parent callback
    }
    setEditingId(null); // exit edit mode regardless of save/cancel
  };

  const handleConfirmDelete = () => {
    if (deleteConfirmId) {
      onDelete(deleteConfirmId); // fire the delete via parent callback
    }
    setDeleteConfirmId(null); // close the modal after action
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

        <div
          ref={menuContainerRef}
          className="flex-1 overflow-y-auto px-3 py-2 space-y-1 custom-scrollbar"
        >
          {sortedSessions.map((session) => (
            <div key={session.id} className="relative">
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
                  className={`w-full text-left pl-3 pr-10 py-2.5 rounded-lg text-sm truncate transition-all flex items-center gap-2 ${currentSessionId === session.id ? "bg-luxury-light text-white shadow-sm" : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200"}`}
                >
                  {session.is_pinned && (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 text-luxury-accent shrink-0 rotate-45">
                      <path d="M16 4a1 1 0 0 1 1 1v5l2 2v2H5v-2l2-2V5a1 1 0 0 1 1-1h8zM12 20a1 1 0 0 1-1-1v-2h2v2a1 1 0 0 1-1 1z" />
                    </svg>
                  )}
                  <span className="truncate">{session.title}</span>
                </button>
              )}

              {/* Three-dot trigger — always visible, works on touch.
                  Why always visible: hover doesn't exist on mobile. Discoverability > tidiness. */}
              {!editingId && (
                <button
                  data-session-menu
                  onClick={(e) => {
                    e.stopPropagation(); // don't select the session when opening the menu
                    setMenuOpenId(menuOpenId === session.id ? null : session.id); // toggle; opening another closes this one
                  }}
                  className="absolute right-1 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-slate-500 hover:text-white hover:bg-slate-800 transition-colors"
                  aria-label="Session actions"
                  aria-haspopup="menu"
                  aria-expanded={menuOpenId === session.id}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <circle cx="5" cy="12" r="1.6" />
                    <circle cx="12" cy="12" r="1.6" />
                    <circle cx="19" cy="12" r="1.6" />
                  </svg>
                </button>
              )}

              {/* Popover menu — rendered only for the open session, right-aligned under the trigger. */}
              {menuOpenId === session.id && (
                <div
                  data-session-menu
                  role="menu"
                  className="absolute right-1 top-[calc(100%-6px)] z-30 w-36 bg-[#12141B] border border-slate-700 rounded-lg shadow-xl py-1 animate-fade-in"
                  onClick={(e) => e.stopPropagation()} // clicks inside the menu must not bubble to the row
                >
                  <button
                    role="menuitem"
                    onClick={() => { onTogglePin(session.id); setMenuOpenId(null); }} // pin/unpin then close
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <line x1="12" y1="17" x2="12" y2="22" /><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.55V6a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4.55a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
                    </svg>
                    {session.is_pinned ? "Unpin" : "Pin"}
                  </button>

                  <button
                    role="menuitem"
                    onClick={() => { setEditingId(session.id); setEditTitle(session.title); setMenuOpenId(null); }} // enter rename mode, close menu
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                    </svg>
                    Rename
                  </button>

                  <button
                    role="menuitem"
                    onClick={() => { setDeleteConfirmId(session.id); setMenuOpenId(null); }} // open delete modal, close menu
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                      <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                    Delete
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

      <DeleteConfirmModal
        isOpen={deleteConfirmId !== null}
        onCancel={() => setDeleteConfirmId(null)}
        onConfirm={handleConfirmDelete}
      />
    </>
  );
}