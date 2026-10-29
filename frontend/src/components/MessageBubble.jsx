import ReactMarkdown from 'react-markdown';
import { useState } from "react";

// Convert the LLM's markdown string into clean plain text for the clipboard.
// Why: users copy answers into emails, Word docs, or back into the chat input.
// Raw markdown like **bold** and ### headings looks unprofessional outside the UI.
// This preserves every word and the list structure (each bullet on its own line)
// while stripping every markdown symbol.
function markdownToPlainText(md) {
  if (!md) return "";
  return md
    // Headings: "### Title" -> "Title"
    .replace(/^#{1,6}\s+/gm, "")
    // Bold and italic: "**x**", "__x__", "*x*", "_x_" -> "x"
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(\*|_)(.*?)\1/g, "$2")
    // Inline code: "`x`" -> "x"
    .replace(/`([^`]+)`/g, "$1")
    // Code fences: "```lang\n...\n```" -> "..."
    .replace(/```[\s\S]*?```/g, (block) =>
      block.replace(/```[a-zA-Z]*\n?/, "").replace(/```$/, "").trim()
    )
    // Links: "[text](url)" -> "text (url)"
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)")
    // Horizontal rules: "---" or "***" on their own line -> remove
    .replace(/^[-*_]{3,}\s*$/gm, "")
    // Blockquote markers: "> text" -> "text"
    .replace(/^>\s?/gm, "")
    // Keep list markers (-, *, +) but normalize * and + to "-"
    .replace(/^(\s*)[*+]\s+/gm, "$1- ")
    // Collapse runs of 3+ blank lines into 2
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export default function MessageBubble({ role, content, sources, isLoading, onEdit }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    // Why markdownToPlainText: strips **bold**, ### headings, `code`, and link
    // syntax so pasted text is clean everywhere (chat input, email, Word doc).
    navigator.clipboard.writeText(markdownToPlainText(content));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };