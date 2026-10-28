import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({ messages, onEdit }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-8 bg-luxury-light custom-scrollbar">
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto animate-fade-in">
          <div className="w-16 h-16 bg-luxury rounded-2xl flex items-center justify-center mb-6 shadow-premium border border-slate-700">
            <svg className="w-8 h-8 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          </div>
          <h2 className="text-2xl font-serif font-semibold text-white mb-3 tracking-tight">
            What would you like to know?
          </h2>
          <p className="text-[15px] text-slate-400 leading-relaxed max-w-sm mx-auto mb-8">
            Ask me anything about the VARA Company, Technology, Market Conduct, or Compliance Rulebooks. I will find the exact rules and cite them for you.
          </p>
          
          {/* Suggested Prompts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
            <div className="p-3 bg-luxury/50 rounded-lg border border-slate-700/50 text-left text-xs text-slate-300 hover:bg-luxury cursor-default">
              "What is the required Paid-Up Capital for a Broker-Dealer?"
            </div>
            <div className="p-3 bg-luxury/50 rounded-lg border border-slate-700/50 text-left text-xs text-slate-300 hover:bg-luxury cursor-default">
              "How quickly must a VASP acknowledge a complaint?"
            </div>
            <div className="p-3 bg-luxury/50 rounded-lg border border-slate-700/50 text-left text-xs text-slate-300 hover:bg-luxury cursor-default">
              "What are the rules for Threat Led Penetration Testing?"
            </div>
            <div className="p-3 bg-luxury/50 rounded-lg border border-slate-700/50 text-left text-xs text-slate-300 hover:bg-luxury cursor-default">
              "How long must records be retained?"
            </div>
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
              onEdit={onEdit}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}