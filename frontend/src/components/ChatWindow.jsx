import { useEffect, useRef, useLayoutEffect } from "react";
import MessageBubble from "./MessageBubble.jsx";

function LoadingSpinner() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-slate-700 border-t-brand-500 animate-spin" />
    </div>
  );
}

export default function ChatWindow({ messages, onEdit, isLoading, onViewSources }) {
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

  useLayoutEffect(() => {
    if (isLoading) return;
    if (!scrollContainerRef.current) return;
    if (messages.length === 0) return;

    const prevCount = prevCountRef.current;
    const currCount = messages.length;
    const delta = currCount - prevCount;
    prevCountRef.current = currCount;

    if (delta > 0 || prevCount === 0) {
      scrollToBottom(false);
    } else {
      const el = scrollContainerRef.current;
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (distance < 150) {
        scrollToBottom(false);
      }
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (isLoading) return;
    const lastMsg = messages[messages.length - 1];
    if (!lastMsg) return;
    if (lastMsg.isLoading) return;

    let cancelled = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (cancelled) return;
        const el = scrollContainerRef.current;
        if (!el) return;
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
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
              isLoading={msg.isLoading}
              onEdit={onEdit}
              onViewSources={onViewSources}
            />
          ))}
        </div>
      )}
    </div>
  );
}