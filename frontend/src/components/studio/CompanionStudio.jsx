import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import html2pdf from 'html2pdf.js';
import 'katex/dist/katex.min.css';
import {
  Sparkles,
  FileText,
  Zap,
  Layers,
  BookOpen,
  Copy,
  Check,
  Download,
  RotateCw,
  Search,
  CheckCircle2,
  Atom,
  FlaskConical,
  Calculator,
  Compass,
  ArrowRight,
  Printer,
  FileDown,
} from 'lucide-react';

const PRESET_TOPICS = [
  {
    subject: 'Physics',
    icon: Atom,
    color: 'indigo',
    topics: [
      'Rotational Dynamics & Pure Rolling',
      'Thermodynamics Cycles & Carnot Engine',
      'Electrostatics & Gauss\'s Law',
      'Ray Optics & Wave Optics',
      'Electromagnetic Induction & Lenz\'s Law',
    ],
  },
  {
    subject: 'Chemistry',
    icon: FlaskConical,
    color: 'emerald',
    topics: [
      'VSEPR Theory & Molecular Geometry',
      'Chemical Equilibrium & Le Chatelier',
      'Chemical Thermodynamics & Spontaneity',
      'Coordination Compounds & Isomerism',
      'Organic Reaction Mechanisms & Stereochemistry',
    ],
  },
  {
    subject: 'Mathematics',
    icon: Calculator,
    color: 'purple',
    topics: [
      'Definite Integrals & King\'s Rule',
      'Conic Sections Standard Equations & Tangents',
      'Differential Equations & Integrating Factors',
      'Vectors & 3D Geometry',
      'Matrices, Determinants & System of Equations',
    ],
  },
];

const ARTIFACT_TYPES = [
  {
    id: 'formula_sheet',
    label: 'Formula Sheet',
    icon: FileText,
    desc: 'Exhaustive formulas, constants, and display LaTeX blocks',
  },
  {
    id: 'cheat_sheet',
    label: 'Cheat Sheet',
    icon: Zap,
    desc: 'High-yield exam revision, JEE traps, shortcuts & roadmaps',
  },
  {
    id: 'flashcards',
    label: 'Flashcards',
    icon: Layers,
    desc: 'Interactive concept cards with tricky front prompts & back derivations',
  },
];

const PROFICIENCY_LEVELS = [
  { id: 'Foundational', label: 'Foundational', badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
  { id: 'JEE Main', label: 'JEE Main', badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
  { id: 'JEE Advanced', label: 'JEE Advanced', badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30' },
];

export default function CompanionStudio() {
  const [selectedTopic, setSelectedTopic] = useState('Rotational Dynamics & Pure Rolling');
  const [customTopicInput, setCustomTopicInput] = useState('');
  const [artifactType, setArtifactType] = useState('formula_sheet');
  const [proficiency, setProficiency] = useState('JEE Advanced');

  const [isLoading, setIsLoading] = useState(false);
  const [isExportingPDF, setIsExportingPDF] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [artifactMarkdown, setArtifactMarkdown] = useState('');
  const [ragContextUsed, setRagContextUsed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const contentRef = useRef(null);

  const loadingSteps = [
    'Retrieving syllabus knowledge chunks from local Qdrant Vector DB...',
    'Grounding formulas and boundary conditions in JEE Advanced scope...',
    'Synthesizing rigorous mathematical expressions with Gemini-3.6-Flash...',
    'Rendering KaTeX formulas and structure layout...',
  ];

  // Rotate loading step messages during generation
  useEffect(() => {
    let interval;
    if (isLoading) {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev + 1) % loadingSteps.length);
      }, 2400);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleGenerate = async (
    targetTopic = selectedTopic,
    targetType = artifactType,
    targetProficiency = proficiency
  ) => {
    const topicToUse = customTopicInput.trim() || targetTopic;
    if (!topicToUse) return;

    setIsLoading(true);
    setErrorMsg(null);

    const apiUrl =
      window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000/api/v1/studio/generate'
        : '/api/v1/studio/generate';

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: topicToUse,
          artifact_type: targetType,
          proficiency: targetProficiency,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      setArtifactMarkdown(data.artifact_markdown || '');
      setRagContextUsed(Boolean(data.rag_context_used));
    } catch (err) {
      console.error('Studio Generation Error:', err);
      setErrorMsg(err.message || 'Failed to generate study artifact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!artifactMarkdown) return;
    navigator.clipboard.writeText(artifactMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!artifactMarkdown) return;
    const blob = new Blob([artifactMarkdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const safeTopic = (customTopicInput || selectedTopic).toLowerCase().replace(/[^a-z0-9]+/g, '_');
    link.download = `JEE_${safeTopic}_${artifactType}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // PDF Export using html2pdf.js with ink-friendly light theme print styles
  const handleDownloadPDF = () => {
    if (!contentRef.current || !artifactMarkdown || isExportingPDF) return;

    setIsExportingPDF(true);
    const element = contentRef.current;

    // Apply PDF print styles to ensure white background and dark text for printer ink savings
    element.classList.add('pdf-print-export');

    const opt = {
      margin: 10,
      filename: 'ActiveMentor_CheatSheet.pdf',
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    };

    html2pdf()
      .set(opt)
      .from(element)
      .save()
      .then(() => {
        element.classList.remove('pdf-print-export');
        setIsExportingPDF(false);
      })
      .catch((err) => {
        console.error('❌ [PDF Export Error]:', err);
        element.classList.remove('pdf-print-export');
        setIsExportingPDF(false);
      });
  };

  return (
    <div className="space-y-6">
      {/* Inline styles for ink-friendly PDF print rendering */}
      <style>{`
        .pdf-print-export {
          background-color: #ffffff !important;
          color: #0f172a !important;
          padding: 24px !important;
          border: none !important;
          box-shadow: none !important;
        }
        .pdf-print-export * {
          color: #0f172a !important;
          background-color: transparent !important;
          border-color: #e2e8f0 !important;
          text-shadow: none !important;
        }
        .pdf-print-export h1,
        .pdf-print-export h2,
        .pdf-print-export h3,
        .pdf-print-export strong {
          color: #1e1b4b !important;
        }
        .pdf-print-export .katex,
        .pdf-print-export .katex-html {
          color: #0f172a !important;
        }
      `}</style>

      {/* Studio Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Compass className="w-3.5 h-3.5" />
            <span>Companion Revision & Artifact Studio</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            JEE Companion Studio
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300">
              Qdrant RAG Powered
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Synthesize authoritative formula sheets, fast-revision cheat sheets, and conceptual flashcards grounded directly in the official JEE Main & Advanced syllabus.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Download PDF Button */}
          <button
            type="button"
            onClick={handleDownloadPDF}
            disabled={!artifactMarkdown || isLoading || isExportingPDF}
            className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-white border border-indigo-500/40 text-xs font-semibold px-4 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-40"
            title="Export high-resolution PDF cheat sheet"
          >
            {isExportingPDF ? (
              <RotateCw className="w-4 h-4 animate-spin text-indigo-400" />
            ) : (
              <FileDown className="w-4 h-4 text-indigo-400" />
            )}
            <span>{isExportingPDF ? 'Exporting...' : 'Download PDF'}</span>
          </button>

          <button
            type="button"
            onClick={() => handleGenerate()}
            disabled={isLoading}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                <span>Synthesizing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Synthesize Artifact</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Sidebar: Controls & Topic Picker */}
        <div className="lg:col-span-4 space-y-5">
          {/* 1. Artifact Type Selector */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
              1. Choose Artifact Type
            </h3>
            <div className="grid grid-cols-1 gap-2">
              {ARTIFACT_TYPES.map((type) => {
                const IconComponent = type.icon;
                const isSelected = artifactType === type.id;
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setArtifactType(type.id)}
                    className={`text-left p-3 rounded-xl border transition-all flex items-start gap-3 ${
                      isSelected
                        ? 'bg-indigo-950/60 border-indigo-500/80 text-slate-100 shadow-md shadow-indigo-950/40 ring-1 ring-indigo-500/40'
                        : 'bg-slate-950/40 hover:bg-slate-800/60 border-slate-800/80 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div
                      className={`p-2 rounded-lg ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-800'
                      }`}
                    >
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-200">{type.label}</div>
                      <div className="text-[11px] text-slate-400 leading-snug mt-0.5">{type.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Proficiency Filter */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-indigo-400" />
              2. Target Proficiency
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {PROFICIENCY_LEVELS.map((level) => {
                const isSelected = proficiency === level.id;
                return (
                  <button
                    key={level.id}
                    type="button"
                    onClick={() => setProficiency(level.id)}
                    className={`py-2 px-1.5 rounded-xl text-center text-xs font-semibold border transition-all ${
                      isSelected
                        ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/30'
                        : 'bg-slate-950/50 hover:bg-slate-800/60 text-slate-400 border-slate-800/80'
                    }`}
                  >
                    {level.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Syllabus & Topic Browser */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              3. Topic Browser
            </h3>

            {/* Custom Topic Input */}
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-slate-400">Custom JEE Topic / Concept</label>
              <div className="relative">
                <input
                  type="text"
                  value={customTopicInput}
                  onChange={(e) => setCustomTopicInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleGenerate(customTopicInput, artifactType, proficiency);
                    }
                  }}
                  placeholder="e.g. King's Rule Integration, Carnot Cycle..."
                  className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                />
                {customTopicInput && (
                  <button
                    type="button"
                    onClick={() => handleGenerate(customTopicInput, artifactType, proficiency)}
                    className="absolute right-1.5 top-1.5 p-1 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 text-xs"
                    title="Generate for custom topic"
                  >
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Preset Curriculum Modules */}
            <div className="pt-2 border-t border-slate-800 space-y-2">
              <label className="text-[11px] font-medium text-slate-400">High-Yield Curriculum Modules</label>
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {PRESET_TOPICS.map((category) => {
                  const CategoryIcon = category.icon;
                  return (
                    <div key={category.subject} className="space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 px-1">
                        <CategoryIcon className="w-3 h-3 text-indigo-400" />
                        <span>{category.subject}</span>
                      </div>
                      <div className="space-y-1">
                        {category.topics.map((t) => {
                          const isCurrent = !customTopicInput && selectedTopic === t;
                          return (
                            <button
                              key={t}
                              type="button"
                              onClick={() => {
                                setCustomTopicInput('');
                                setSelectedTopic(t);
                              }}
                              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-all flex items-center justify-between ${
                                isCurrent
                                  ? 'bg-indigo-600/20 text-indigo-300 font-semibold border border-indigo-500/30'
                                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                              }`}
                            >
                              <span className="truncate">{t}</span>
                              {isCurrent && <CheckCircle2 className="w-3 h-3 text-indigo-400 flex-shrink-0 ml-1" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right Area: Document Viewer */}
        <div className="lg:col-span-8 space-y-4">
          {/* Document Header & Actions */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl px-5 py-3.5 backdrop-blur-md flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100">
                  {customTopicInput.trim() || selectedTopic}
                </h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    {artifactType.replace('_', ' ')}
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-[10px] text-indigo-400 font-semibold">{proficiency}</span>
                  {ragContextUsed && (
                    <>
                      <span className="text-slate-600">•</span>
                      <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Qdrant Grounded
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyMarkdown}
                disabled={!artifactMarkdown || isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all disabled:opacity-40"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadPDF}
                disabled={!artifactMarkdown || isLoading || isExportingPDF}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-950/70 hover:bg-indigo-900 text-indigo-300 hover:text-white border border-indigo-700/60 transition-all disabled:opacity-40"
                title="Export as PDF"
              >
                {isExportingPDF ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileDown className="w-3.5 h-3.5" />
                )}
                <span>PDF</span>
              </button>

              <button
                type="button"
                onClick={handleDownload}
                disabled={!artifactMarkdown || isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all disabled:opacity-40"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download .md</span>
              </button>

              <button
                type="button"
                onClick={() => handleGenerate()}
                disabled={isLoading}
                className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition-all disabled:opacity-40"
                title="Regenerate"
              >
                <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Document Content View & Printable Target Area */}
          <div
            ref={contentRef}
            id="printable-studio-content"
            className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-6 sm:p-8 min-h-[560px] relative overflow-hidden backdrop-blur-md shadow-inner"
          >
            {/* Error Message */}
            {errorMsg && (
              <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
                <p className="font-bold mb-1">Synthesis Failed:</p>
                <p>{errorMsg}</p>
              </div>
            )}

            {/* Pulsing Loading State */}
            {isLoading ? (
              <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center p-6 space-y-4">
                <div className="relative">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-blue-500 animate-spin blur-md opacity-70" />
                  <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-indigo-500/50 absolute inset-0 flex items-center justify-center shadow-xl">
                    <Sparkles className="w-7 h-7 text-indigo-400 animate-pulse" />
                  </div>
                </div>

                <div className="text-center space-y-1.5 max-w-md">
                  <h4 className="text-sm font-bold text-slate-100">Generating JEE Study Artifact</h4>
                  <p className="text-xs text-indigo-300 font-medium animate-pulse">{loadingSteps[loadingStep]}</p>
                  <p className="text-[11px] text-slate-500">Querying Qdrant Vector DB & Synthesizing KaTeX Formulas</p>
                </div>

                {/* Skeleton placeholders */}
                <div className="w-full max-w-lg space-y-2.5 pt-4 opacity-40">
                  <div className="h-4 bg-slate-800 rounded w-3/4 animate-pulse" />
                  <div className="h-3 bg-slate-800 rounded w-full animate-pulse" />
                  <div className="h-3 bg-slate-800 rounded w-5/6 animate-pulse" />
                  <div className="h-10 bg-slate-800/60 rounded-xl w-full animate-pulse" />
                </div>
              </div>
            ) : null}

            {/* Rendered Markdown Document */}
            {artifactMarkdown ? (
              <div className="studio-markdown prose prose-invert max-w-none prose-headings:text-slate-100 prose-h1:text-xl prose-h1:font-extrabold prose-h2:text-base prose-h2:font-bold prose-h2:border-b prose-h2:border-slate-800 prose-h2:pb-2 prose-h3:text-sm prose-h3:font-semibold prose-p:text-xs prose-p:leading-relaxed prose-p:text-slate-300 prose-li:text-xs prose-li:text-slate-300 prose-strong:text-indigo-300 prose-table:text-xs prose-th:text-slate-200 prose-td:text-slate-300">
                <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                  {artifactMarkdown}
                </ReactMarkdown>
              </div>
            ) : (
              !isLoading && (
                <div className="flex flex-col items-center justify-center h-96 text-center text-slate-500 space-y-3">
                  <FileText className="w-12 h-12 text-slate-700 stroke-1" />
                  <div>
                    <h4 className="text-sm font-semibold text-slate-400">No Artifact Generated Yet</h4>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm">
                      Select a topic from the sidebar and click Synthesize Artifact to generate your LaTeX study document.
                    </p>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
