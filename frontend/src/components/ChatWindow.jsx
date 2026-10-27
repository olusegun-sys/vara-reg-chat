import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

// Scrollable list of messages.
// Why a separate component:
// - The scroll-to-bottom logic is subtle and stateful. Isolating it keeps App.jsx clean.
// - Empty state is handled here, not in App.jsx, so the layout is self-contained.

export default function ChatWindow({ messages }) {
  const bottomRef = useRef(null);

  // Auto-scroll to the newest message whenever the list changes.
  // Why useEffect: refs are only reliable after render, so scrolling must happen post-render.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto chat-scroll px-3 sm:px-6 py-4 bg-slate-50">
      {messages.length === 0 ? (
        <div className="h-full flex items-center justify-center">
          <div className="text-center max-w-md">
            <h2 className="text-lg font-semibold text-slate-700 mb-2">
              Ask the rulebook
            </h2>
            <p className="text-sm text-slate-500">
              Type a question below to get a cited answer grounded in the
              VARA Compliance and Risk Management Rulebook.
            </p>
          </div>
        </div>
      ) : (
        <div className="max-w-3xl mx-auto space-y-3">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
              isLoading={msg.isLoading}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}