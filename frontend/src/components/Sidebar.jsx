import { useState } from "react";

export default function Sidebar({ sessions, currentSessionId, onSelectSession, onNewChat, onRename, onDelete, onTogglePin }) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const handleEditSubmit = (id) => {
    if (editTitle.trim()) onRename(id, editTitle.trim());
    setEditingId(null);
  };

  return (
    <div className="w-64 bg-slate-900 text-slate-300 flex flex-col h-full border-r border-slate-800 hidden md:flex">
      <div className="p-3">
        <button onClick={onNewChat} className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg border border-slate-700 hover:bg-slate-800 transition-colors text-sm font-medium text-white">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {sessions.map((session) => (
          <div key={session.id} className="relative group">
            {editingId === session.id ? (
              <input
                type="text" autoFocus value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => handleEditSubmit(session.id)}
                onKeyDown={(e) => e.key === "Enter" && handleEditSubmit(session.id)}
                className="w-full text-sm bg-slate-800 text-white px-2 py-1.5 rounded border border-slate-600 focus:outline-none"
              />
            ) : (
              <button
                onClick={() => onSelectSession(session.id)}
                className={`w-full text-left pl-3 pr-8 py-2 rounded-lg text-sm truncate transition-colors flex items-center gap-2 ${currentSessionId === session.id ? "bg-slate-800 text-white" : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200"}`}
              >
                {session.is_pinned && (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 text-brand-500 shrink-0 rotate-45">
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
                <button onClick={(e) => { e.stopPropagation(); onDelete(session.id); }} className="p-1 text-slate-400 hover:text-red-400" title="Delete">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                    <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="p-4 border-t border-slate-800 text-xs text-slate-500 text-center">Regulatory Knowledge Base</div>
    </div>
  );
}