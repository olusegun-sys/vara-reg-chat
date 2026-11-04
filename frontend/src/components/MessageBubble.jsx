import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from "react";

function markdownToPlainText(md) {
  if (!md) return "";
  return md
    .replace(/```[\s\S]*?```/g, (block) =>
      block.replace(/^```[a-zA-Z]*\n?/, "").replace(/\n?```$/, "").trim()
    )
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(\*|_)(.*?)\1/g, "$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)")
    .replace(/^[-*_]{3,}\s*$/gm, "")
    .replace(/^>\s?/gm, "")
    .replace(/^(\s*)[*+]\s+/gm, "$1- ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export default function MessageBubble({ role, content, sources, isLoading, onEdit }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  const isWebSearch = sources && sources.some(s => s.section === "Web Search Result");

  const handleCopy = () => {
    navigator.clipboard.writeText(markdownToPlainText(content));
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
      <div
        className={`
          max-w-[95%] sm:max-w-[85%] rounded-2xl px-4 sm:px-5 py-3 sm:py-4 shadow-sm text-[15px]
          ${isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-[#12141B] text-slate-200 border border-slate-800/60 rounded-bl-sm shadow-premium"}
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
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
                    li: ({ node, ...props }) => <li className="text-slate-200" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-semibold text-white" {...props} />,
                    a: ({ node, ...props }) => <a className="text-brand-400 hover:underline" {...props} />,
                    
                    table: ({ node, ...props }) => (
                      <div className="w-full min-w-0 overflow-x-auto my-4 border border-slate-700/60 rounded-lg shadow-sm">
                        <table className="w-full text-[13.5px] text-left border-collapse" {...props} />
                      </div>
                    ),
                    thead: ({ node, ...props }) => <thead className="bg-slate-800/80 border-b border-slate-700/60" {...props} />,
                    tbody: ({ node, ...props }) => <tbody className="divide-y divide-slate-700/40 bg-slate-900/20" {...props} />,
                    tr: ({ node, ...props }) => <tr className="hover:bg-slate-800/40 transition-colors" {...props} />,
                    th: ({ node, ...props }) => <th className="px-3 sm:px-4 py-2 sm:py-2.5 font-medium text-slate-200 whitespace-nowrap" {...props} />,
                    td: ({ node, ...props }) => <td className="px-3 sm:px-4 py-2 sm:py-2.5 text-slate-300 align-top" {...props} />,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}

            {!isUser && isWebSearch && (
              <div className="mt-3 flex items-start gap-2 bg-amber-900/20 border border-amber-700/40 rounded-lg p-2.5">
                <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
                <p className="text-[11px] text-amber-200/90 leading-tight">
                  <strong className="font-semibold text-amber-200">Web Search Fallback:</strong> This answer includes live web results because it falls outside the ingested rulebooks. Verify independently.
                </p>
              </div>
            )}

            {sources && sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-700/60 w-full">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Documents Referenced
                </p>
                <div className="flex flex-col gap-1.5 w-full">
                  {/* Deduplicate by document AND section to show the exact part */}
                  {[...new Map(sources.map(s => [`${s.document}-${s.section}`, s])).values()].map((sourceEntry, i) => {
                    const docName = sourceEntry.document;
                    const url = sourceEntry.source_url;
                    const sectionName = sourceEntry.section && sourceEntry.section !== "General" && sourceEntry.section !== "Web Search Result"
                      ? ` (${sourceEntry.section})` 
                      : "";
                    
                    const baseClasses = "group flex items-start w-full text-[12px] bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 hover:text-white px-3 py-2 rounded-lg border border-slate-700/50 transition-all text-left";
                    
                    const innerContent = (
                      <>
                        <svg className="w-3.5 h-3.5 mr-2 mt-[2px] text-brand-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <span className="break-words whitespace-normal leading-tight flex-1 pr-2">
                          {docName}<span className="text-slate-400 font-medium">{sectionName}</span>
                        </span>
                        {url && (
                          <svg className="w-3.5 h-3.5 text-slate-500 group-hover:text-brand-400 transition-colors shrink-0 mt-[1px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                          </svg>
                        )}
                      </>
                    );

                    return url ? (
                      <a key={i} href={url} target="_blank" rel="noopener noreferrer" className={baseClasses} title={`Open ${docName} on the official source site`}>
                        {innerContent}
                      </a>
                    ) : (
                      <div key={i} className={baseClasses}>{innerContent}</div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {!isLoading && (
        <div className={`flex items-center gap-1 mt-1.5 px-1 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
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