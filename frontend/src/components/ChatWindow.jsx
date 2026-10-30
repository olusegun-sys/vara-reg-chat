import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

// Single rotating ring spinner — minimal, matches DeepSeek/ChatGPT style.
// Why a ring instead of dots: cleaner, more professional, no text label.
// The ring uses border-t-brand-500 for the accent color and border on the
// other three sides for the track. Tailwind's animate-spin does the rotation.
function LoadingSpinner() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-slate-700 border-t-brand-500 animate-spin" />
    </div>
  );
}

export default function ChatWindow({ messages, onEdit, isLoading }) {
  const bottomRef = useRef(null);
  // Track the previous message count so we can decide scroll behavior:
  // - When message count increases by 1 during a session → smooth scroll.
  // - When the message count jumps by more than 1 (session load) → instant scroll.
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (!bottomRef.current) return;
    if (isLoading) return;

    const prev = prevCountRef.current;
    const curr = messages.length;
    const delta = curr - prev;

    if (delta === 1) {
      bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    } else if (delta > 1 || prev === 0) {
      bottomRef.current.scrollIntoView({ behavior: "auto", block: "end" });
    }

    prevCountRef.current = curr;
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-8 bg-luxury-light custom-scrollbar">
      {isLoading ? (
        <LoadingSpinner />
      ) : messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto animate-fade-in">
          <div className="w-16 h-16 bg-luxury rounded-2xl flex items-center justify-center mb-6 shadow-premium border border-slate-700">
            <svg className="w-8 h-8 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          </div>
          <h2 className="text-2xl font-serif font-semibold text-white tracking-tight">
            What would you like to know?
          </h2>
        </div>
      ) : (
        <div className="max-w-3xl mx-auto space-y-6 pb-4">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
              isLoading={msg.isLoading}
              onEdit={onEdit}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}