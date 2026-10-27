import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 bg-white custom-scrollbar">
      {messages.length === 0 ? (
        <div className="h-full flex items-center justify-center">
          <div className="text-center max-w-md animate-fade-in">
            <div className="w-16 h-16 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-sm border border-brand-100">
              <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <h2 className="text-2xl font-serif font-semibold text-slate-800 mb-3 tracking-tight">
              Regulatory Intelligence
            </h2>
            <p className="text-sm text-slate-500 leading-relaxed max-w-sm mx-auto">
              Query the VARA Compliance and Risk Management Rulebook. 
              Get instant, citation-backed answers grounded in the text.
            </p>
          </div>
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
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}