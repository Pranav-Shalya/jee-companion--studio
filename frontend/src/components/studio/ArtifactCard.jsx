import React, { useState } from 'react';
import { Download, FileText, ChevronDown, ChevronUp, Tag, Copy, Check } from 'lucide-react';
import LatexRenderer from '../chat/LatexRenderer';
import { api } from '../../services/api';

const ARTIFACT_TYPE_LABELS = {
  formula_sheet: { label: 'Formula Sheet', color: 'bg-indigo-950/50 text-indigo-300 border-indigo-800' },
  revision_note: { label: 'Revision Summary', color: 'bg-emerald-950/50 text-emerald-300 border-emerald-800' },
  mindmap: { label: 'Mindmap & Guide', color: 'bg-amber-950/50 text-amber-300 border-amber-800' },
  pyq_breakdown: { label: 'PYQ Breakdown', color: 'bg-purple-950/50 text-purple-300 border-purple-800' },
};

export default function ArtifactCard({ artifact }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const typeConfig =
    ARTIFACT_TYPE_LABELS[artifact.artifact_type] || {
      label: artifact.artifact_type,
      color: 'bg-slate-800 text-slate-300 border-slate-700',
    };

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([artifact.content], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = artifact.download_filename || `${artifact.title.replace(/\s+/g, '_')}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-xl transition-all">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded border ${typeConfig.color}`}>
              {typeConfig.label}
            </span>
            <span className="text-[11px] font-medium text-slate-400">
              {artifact.subject} • {artifact.topic}
            </span>
          </div>
          <h3 className="text-sm font-bold text-slate-100">{artifact.title}</h3>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleCopy}
            title="Copy Markdown"
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-all"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            title="Download Artifact"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-indigo-700/60 bg-indigo-950/60 hover:bg-indigo-900/70 text-indigo-300 text-xs font-semibold shadow-sm transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download</span>
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-300 mb-3">{artifact.description}</p>

      {/* Tags */}
      {artifact.tags && artifact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {artifact.tags.map((tag, idx) => (
            <span key={idx} className="text-[10px] bg-slate-950 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-md">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Expand / Collapse Preview */}
      <div className="border-t border-slate-800/80 pt-2.5">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-200 py-1 transition-all"
        >
          <span className="font-medium">{isExpanded ? 'Hide Document Preview' : 'Show LaTeX & Math Preview'}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {isExpanded && (
          <div className="mt-3 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs max-h-96 overflow-y-auto">
            <LatexRenderer content={artifact.content} />
          </div>
        )}
      </div>
    </div>
  );
}
