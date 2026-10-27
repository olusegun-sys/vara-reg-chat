import ReactMarkdown from 'react-markdown';

// One message in the chat. Handles three states:
// 1. User message (right-aligned, brand color)
// 2. Assistant message with citations (left-aligned, light gray)
// 3. Loading indicator (three pulsing dots)
//
// Why citations are rendered separately:
// - The LLM embeds 【Page 8 | ...】 inline in the answer text.
// - We ALSO show a clean list of sources below so the user can see
//   exactly which pages were consulted, without parsing the answer.
// - This is what makes a compliance tool trustworthy: visible evidence.

export default function MessageBubble({ role, content, sources, isLoading }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`
          max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm
          ${isUser
            ? "bg-brand-600 text-white rounded-br-md"
            : "bg-white text-slate-800 border border-slate-200 rounded-bl-md"}
        `}
      >
        {isLoading ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
            <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
            <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          </div>
        ) : (
          <>
            {isUser ? (
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {content}
              </p>
            ) : (
              <div className="text-sm leading-relaxed overflow-hidden">
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                    // Ensures long unbroken strings don't break the layout
                    a: ({ node, ...props }) => <a className="text-brand-600 hover:underline break-words" {...props} />
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}

            {sources && sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-200/70">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                  Sources
                </p>
                <ul className="space-y-0.5">
                  {sources.map((src, i) => (
                    <li key={i} className="text-xs text-slate-500">
                      <span className="font-medium text-slate-700">
                        Page {src.page}
                      </span>
                      {src.section && src.section !== "General" && (
                        <span> · {src.section}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}