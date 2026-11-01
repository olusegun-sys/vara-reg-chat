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
  // Ref to the SCROLL CONTAINER, not a marker div. Scrolling the container
  // directly with scrollTop = scrollHeight is deterministic and NEVER scrolls
  // the outer page — unlike scrollIntoView, which walks the ancestor chain
  // and can scroll parent containers unexpectedly.
  const scrollContainerRef = useRef(null);
  const prevMessageCountRef = useRef(0);
  const lastScrollTimeRef = useRef(0);
  const rafPendingRef = useRef(false);

  // Scroll the container to the bottom, batched per animation frame.
  // Why rAF: during streaming, setMessages fires per token (~50-100x/sec).
  // Without batching, we'd call scrollTop 100 times per second, causing the
  // browser to abandon/restart scroll animations. rAF coalesces all scroll
  // requests in a single frame into one actual scroll.
  const scrollToBottom = (smooth = false) => {
    if (!scrollContainerRef.current) return;
    if (rafPendingRef.current) return;

    rafPendingRef.current = true;
    requestAnimationFrame(() => {
      const el = scrollContainerRef.current;
      if (!el) {
        rafPendingRef.current = false;
        return;
      }
      // Direct scrollTop assignment. Always works, never touches page scroll.
      // smooth: we use CSS scroll-behavior instead (see className below) so
      // the browser handles animation natively without our JS fighting it.
      el.scrollTo({
        top: el.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
      lastScrollTimeRef.current = Date.now();
      rafPendingRef.current = false;
    });
  };

  // useLayoutEffect (not useEffect) — fires synchronously AFTER DOM mutations
  // but BEFORE the browser paints. This ensures the scroll happens in the same
  // frame as the content growth, so there's no visible jump.
  useLayoutEffect(() => {
    if (isLoading) return; // session-level spinner: don't scroll

    const prevCount = prevMessageCountRef.current;
    const currCount = messages.length;
    const delta = currCount - prevCount;
    prevMessageCountRef.current = currCount;

    if (currCount === 0) return;

    // New message(s) appended (send flow): delta = 2 because we add both the
    // user message AND the assistant placeholder in one setMessages call.
    // Use smooth scroll only for single-message growth (during session load
    // with pagination, this shouldn't trigger — we want instant).
    if (delta === 2) {
      scrollToBottom(false); // instant on send — no competing animations
    } else if (delta > 2 || prevCount === 0) {
      scrollToBottom(false); // session load — instant
    } else {
      // delta === 0: array reference changed but length same — this is streaming.
      // The last message's content grew. Keep the user pinned to bottom ONLY
      // if they were already near the bottom (don't fight manual scroll-up).
      const el = scrollContainerRef.current;
      if (!el) return;
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      // If user is within 150px of bottom, they want to follow the stream.
      // If they scrolled up further, respect their position (don't yank them down).
      if (distanceFromBottom < 150) {
        scrollToBottom(false); // instant during streaming — no smooth animation
      }
    }
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
            <MessageBubble
              key={msg.id || i}
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