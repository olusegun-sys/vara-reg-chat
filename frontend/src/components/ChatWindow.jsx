import { useEffect, useRef, useLayoutEffect } from "react";
import MessageBubble from "./MessageBubble.jsx";

function LoadingSpinner() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-slate-700 border-t-brand-500 animate-spin" />
    </div>
  );
}

export default function ChatWindow({ messages, onEdit, isLoading }) {
  const scrollContainerRef = useRef(null);
  const prevCountRef = useRef(0);
  const rafPendingRef = useRef(false);

  const scrollToBottom = (smooth = false) => {
    if (!scrollContainerRef.current) return;
    if (rafPendingRef.current) return;
    rafPendingRef.current = true;
    requestAnimationFrame(() => {
      const el = scrollContainerRef.current;
      if (el) {
        el.scrollTo({
          top: el.scrollHeight,
          behavior: smooth ? "smooth" : "auto",
        });
      }
      rafPendingRef.current = false;
    });
  };

  // Primary scroll effect: handles new messages, session loads, and streaming.
  // useLayoutEffect fires synchronously before paint, so the user never sees
  // an intermediate scroll position. rAF batches multiple calls per frame
  // (streaming fires 50-100 setMessages/sec — we don't want 100 scroll calls).
  useLayoutEffect(() => {
    if (isLoading) return;
    if (!scrollContainerRef.current) return;
    if (messages.length === 0) return;

    const prevCount = prevCountRef.current;
    const currCount = messages.length;
    const delta = currCount - prevCount;
    prevCountRef.current = currCount;

    if (delta > 0 || prevCount === 0) {
      // New message(s) or session load → instant scroll
      scrollToBottom(false);
    } else {
      // Same count, content changed → streaming. Only follow if user is
      // within 150px of bottom (respects manual scroll-up).
      const el = scrollContainerRef.current;
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (distance < 150) {
        scrollToBottom(false);
      }
    }
  }, [messages, isLoading]);

  // Belt-and-suspenders: when the last message transitions from isLoading:true
  // to isLoading:false (streaming complete), the DOM re-layouts. Fire one more
  // scroll after two rAF frames to catch any deferred layout.
  // Why two frames: React commits, browser lays out, then paints. The second
  // rAF lands after layout for the final state.
  useEffect(() => {
    if (isLoading) return;
    const lastMsg = messages[messages.length - 1];
    if (!lastMsg) return;
    if (lastMsg.isLoading) return; // still streaming — primary effect handles it

    // Streaming just finished. Wait for layout, then scroll.
    let cancelled = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (cancelled) return;
        const el = scrollContainerRef.current;
        if (!el) return;
        // Only scroll if user is still near bottom (respects manual scroll-up)
        const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
        if (distance < 200) {
          el.scrollTo({ top: el.scrollHeight, behavior: "auto" });
        }
      });
    });
    return () => { cancelled = true; };
  }, [messages, isLoading]);

  return (
    <div
      ref={scrollContainerRef}
      className="flex-1 overflow-y-auto px-4 sm:px-6 py-8 bg-luxury-light custom-scrollbar"
    >
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
            // FIX: key={i}, not key={msg.id || i}.
            // Why: the assistant placeholder has id="temp-ai" during streaming,
            // then App.jsx replaces it with the real Supabase id when streaming
            // finishes. If we use msg.id as key, React sees "temp-ai" → "uuid"
            // and REMOUNTS the entire bubble component — which collapses the
            // scroll container's content height briefly, resetting scrollTop
            // to near zero. That's the "jump to top" the user was seeing.
            // Index is stable because chat messages are append-only. React
            // handles in-place content growth within the same key fine.
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
              isLoading={msg.isLoading}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
    </div>
  );
}