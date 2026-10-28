import ReactMarkdown from 'react-markdown';
import { useState } from "react";

export default function MessageBubble({ role, content, sources, isLoading, onEdit }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const Tooltip = ({ text, children }) => (
    <div className="relative group flex items-center justify-center">
      {children}
      <span className="absolute -top-8 scale-0 transition-all rounded bg-slate-800 p-1.5 text-xs text-white group-hover:scale-100 whitespace-nowrap z-50 shadow-md border border-slate-700">
        {text}
      </span>
    </div>
  );

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} w-full`}>
      
      {/* The Bubble */}
      <div
        className={`
          max-w-[90%] sm:max-w-[85%] rounded-2xl px-4 py-3 sm:px-5 sm:py-4 shadow-sm text-[15px]
          ${isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-[#1E293B] text-slate-200 border border-slate-700/50 rounded-bl-sm shadow-premium"}
        `}
      >
        {isLoading ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="typing-dot w-2 h-2 rounded-full bg-brand-500" />
            <span className="typing-dot w-2 h-2 rounded-full bg-brand-500" />
            <span className="typing-dot w-2 h-2 rounded-full bg-brand-500" />
          </div>
        ) : (
          <>
            {isUser ? (
              <p className="whitespace-pre-wrap break-words leading-relaxed">
                {content}
              </p>
            ) : (
              <div className="leading-relaxed overflow-hidden prose prose-invert max-w-none text-slate-200">
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1 marker:text-brand-500" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1 marker:text-brand-500" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-semibold text-white" {...props} />,
                    a: ({ node, ...props }) => <a className="text-brand-400 hover:underline" {...props} />
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}

            {/* Cleaned up Sources Section */}
            {sources && sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-700/60">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Sources cited
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((src, i) => (
                    <span key={i} className="inline-flex items-center text-[11px] bg-slate-800/80 text-slate-300 px-2 py-1 rounded border border-slate-700/50">
                      <span className="font-medium text-brand-400 mr-1">p.{src.page}</span>
                      <span className="truncate max-w-[120px]">{src.section !== "General" ? src.section : src.document}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {!isLoading && (
        <div className={`flex items-center gap-1 mt-1.5 px-1 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          {/* ... (keep your existing Action Buttons exactly as they are) ... */}
          <Tooltip text={copied ? "Copied!" : "Copy"}>
            <button onClick={handleCopy} className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors">
              {copied ? (
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
              )}
            </button>
          </Tooltip>

          {isUser && (
            <Tooltip text="Edit">
              <button onClick={() => onEdit && onEdit(content)} className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
              </button>
            </Tooltip>
          )}

          {!isUser && (
            <>
              <Tooltip text="Good Response">
                <button className="p-1.5 text-slate-500 hover:text-green-400 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path></svg>
                </button>
              </Tooltip>
              <Tooltip text="Bad Response">
                <button className="p-1.5 text-slate-500 hover:text-red-400 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path></svg>
                </button>
              </Tooltip>
              <Tooltip text="Share">
                <button className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path></svg>
                </button>
              </Tooltip>
            </>
          )}
        </div>
      )}
    </div>
  );
}