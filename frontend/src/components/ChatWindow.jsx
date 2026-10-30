import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

// DeepSeek-style loading indicator: three pulsing dots in the app's accent color.
// Why a custom spinner: shows during session load so users see "loading" instead of
// a jarring jump-scroll from old messages to new ones. Matches the near-black theme.
function LoadingSpinner() {
  return (
    <div className="h-full flex flex-col items-center justify-center">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse" style={{ animationDelay: "0ms" }} />
        <span className="w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse" style={{ animationDelay: "150ms" }} />
        <span className="w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse" style={{ animationDelay: "300ms" }} />
      </div>
      <p className="text-xs text-slate-500 mt-4 tracking-wider uppercase">Loading conversation</p>
    </div>
  );
}

export default function ChatWindow({ messages, onEdit, isLoading }) {
  const bottomRef = useRef(null);
  // Track the previous message count so we can decide scroll behavior:
  // - When message count increases by 1 during a session (streaming chunks, new
  //   message arrives) → smooth scroll (nice UX, matches ChatGPT/DeepSeek).
  // - When the message count jumps by more than 1 (session load) → instant scroll
  //   (no janky top-to-bottom animation).
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (!bottomRef.current) return;
    if (isLoading) return; // don't scroll while spinner is showing

    const prev = prevCountRef.current;
    const curr = messages.length;
    const delta = curr - prev;

    // delta === 1 means "one new message was appended" (normal send flow).
    // delta > 1 or first-ever render means "session just loaded" — jump instantly.
    // delta === 0 means no change (metadata update), do nothing.
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