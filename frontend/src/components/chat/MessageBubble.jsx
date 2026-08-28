import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import {
  Lightbulb,
  GitBranch,
  Calculator,
  Award,
  User,
  AlertCircle,
  HelpCircle,
  Clock,
  Sparkles,
} from 'lucide-react';

const TIER_META = {
  user_question: {
    title: 'Your Doubt',
    icon: User,
    containerClass: 'bg-slate-900/90 border-slate-800 text-slate-100 ml-auto',
    badgeClass: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    iconBg: 'bg-indigo-600/30 text-indigo-400 border-indigo-500/40',
  },
  hint_1: {
    title: 'Tier 1: Conceptual Nudge',
    subtitle: 'Core Concept & Governing Principles',
    icon: Lightbulb,
    containerClass: 'bg-indigo-950/30 border-indigo-500/40 text-slate-200 shadow-indigo-950/20',
    badgeClass: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
    iconBg: 'bg-indigo-500/30 text-indigo-400 border-indigo-500/50',
  },
  hint_2: {
    title: 'Tier 2: Structural Push',
    subtitle: 'Equation Setup & Solution Roadmap',
    icon: GitBranch,
    containerClass: 'bg-blue-950/30 border-blue-500/40 text-slate-200 shadow-blue-950/20',
    badgeClass: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    iconBg: 'bg-blue-500/30 text-blue-400 border-blue-500/50',
  },
  hint_3: {
    title: 'Tier 3: Calculation Guide',
    subtitle: 'Intermediate Algebraic Evaluation',
    icon: Calculator,
    containerClass: 'bg-emerald-950/30 border-emerald-500/40 text-slate-200 shadow-emerald-950/20',
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    iconBg: 'bg-emerald-500/30 text-emerald-400 border-emerald-500/50',
  },
  master_solution: {
    title: 'Master Solution (Verified Math Proof)',
    subtitle: 'Complete Internal Derivation & Verification',
    icon: Award,
    containerClass: 'bg-purple-950/40 border-purple-500/60 text-slate-100 shadow-purple-950/30 ring-1 ring-purple-500/30',
    badgeClass: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    iconBg: 'bg-purple-500/30 text-purple-300 border-purple-500/50',
  },
  info: {
    title: 'System Notice',
    icon: HelpCircle,
    containerClass: 'bg-slate-900/60 border-slate-800 text-slate-300',
    badgeClass: 'bg-slate-800 text-slate-400 border-slate-700',
    iconBg: 'bg-slate-800 text-slate-400 border-slate-700',
  },
  error: {
    title: 'Notice',
    icon: AlertCircle,
    containerClass: 'bg-rose-950/30 border-rose-800/60 text-rose-200',
    badgeClass: 'bg-rose-900/30 text-rose-300 border-rose-800/50',
    iconBg: 'bg-rose-900/40 text-rose-400 border-rose-800/60',
  },
};

/**
 * Normalizes LaTeX delimiters so remark-math & rehype-katex render flawlessly:
 * 1. Replaces \( and \) with $ (inline math)
 * 2. Replaces \[ and \] with $$ (block math)
 * 3. Cleans up escaped brackets and unescaped math expressions.
 */
export function preprocessLatex(content) {
  if (!content || typeof content !== 'string') return '';

  let cleaned = content;

  // Replace block math \[ ... \] with $$ ... $$
  cleaned = cleaned.replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$');
  cleaned = cleaned.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$');

  // Replace inline math \( ... \) with $ ... $
  cleaned = cleaned.replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
  cleaned = cleaned.replace(/\\\(/g, '$').replace(/\\\)/g, '$');

  return cleaned;
}

export default function MessageBubble({ message }) {
  const meta = TIER_META[message.type] || TIER_META.info;
  const Icon = meta.icon;
  const isUser = message.type === 'user_question';

  const timeFormatted = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  const processedContent = preprocessLatex(message.content);

  return (
    <div className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'} my-3`}>
      <div
        className={`max-w-3xl w-full border rounded-2xl p-5 shadow-xl backdrop-blur-md transition-all ${meta.containerClass}`}
      >
        {/* Bubble Header */}
        <div className="flex items-center justify-between gap-3 mb-3 pb-2.5 border-b border-slate-800/60">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-xl border ${meta.iconBg}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold text-slate-100">{message.tierName || meta.title}</h4>
                {message.subject && (
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {message.subject}
                  </span>
                )}
                {message.complexity && (
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                    {message.complexity}
                  </span>
                )}
              </div>
              {meta.subtitle && <p className="text-[11px] text-slate-400">{meta.subtitle}</p>}
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Clock className="w-3 h-3" />
            <span>{timeFormatted}</span>
          </div>
        </div>

        {/* Uploaded User Image (if attached) */}
        {message.image && (
          <div className="mb-3.5">
            <img
              src={message.image}
              alt="Attached problem diagram"
              className="max-h-64 max-w-full rounded-xl border border-indigo-500/30 object-contain bg-slate-950 shadow-md"
            />
          </div>
        )}

        {/* Message Content with ReactMarkdown + remarkMath + rehypeKatex */}
        {processedContent && (
          <div className="prose prose-invert max-w-none text-xs sm:text-sm text-slate-200 leading-relaxed overflow-x-auto space-y-2">
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-4 space-y-1 mb-2">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 space-y-1 mb-2">{children}</ol>,
                li: ({ children }) => <li className="text-slate-300">{children}</li>,
                strong: ({ children }) => <strong className="font-bold text-slate-100">{children}</strong>,
                code: ({ inline, children }) =>
                  inline ? (
                    <code className="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-indigo-300 text-xs font-mono">
                      {children}
                    </code>
                  ) : (
                    <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 overflow-x-auto text-xs font-mono my-2 text-slate-200">
                      <code>{children}</code>
                    </pre>
                  ),
              }}
            >
              {processedContent}
            </ReactMarkdown>
          </div>
        )}

        {/* Action Prompt Note for Hints */}
        {message.canRequestMore && (
          <div className="mt-3.5 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5 text-indigo-400 font-medium">
              <Sparkles className="w-3.5 h-3.5" />
              Pedagogical Guard: Work through the setup above. Use the action bar when you need the next step.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
