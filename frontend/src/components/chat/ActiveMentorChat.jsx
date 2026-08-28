import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Send,
  Sparkles,
  RotateCcw,
  Lightbulb,
  GitBranch,
  Calculator,
  Award,
  ArrowRight,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Paperclip,
  Image as ImageIcon,
  X,
  History,
  Menu,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { useMentorSocket } from '../../hooks/useMentorSocket';
import MessageBubble from './MessageBubble';
import HistorySidebar from './HistorySidebar';

const PROGRESS_STAGES = [
  { level: 1, label: 'Hint 1: Concept', icon: Lightbulb, color: 'text-indigo-400', activeBg: 'bg-indigo-600' },
  { level: 2, label: 'Hint 2: Structure', icon: GitBranch, color: 'text-blue-400', activeBg: 'bg-blue-600' },
  { level: 3, label: 'Hint 3: Calculation', icon: Calculator, color: 'text-emerald-400', activeBg: 'bg-emerald-600' },
  { level: 4, label: 'Master Solution', icon: Award, color: 'text-purple-400', activeBg: 'bg-purple-600' },
];

const SAMPLE_QUESTIONS = {
  Physics: 'A solid sphere of mass M and radius R rolls without slipping down an inclined plane of angle theta. Find its linear acceleration.',
  Chemistry: 'For the equilibrium reaction N2(g) + 3H2(g) <=> 2NH3(g), ΔH < 0. Explain how increasing pressure and temperature shifts equilibrium using Le Chatelier principle.',
  Mathematics: 'Evaluate the definite integral I = \\int_0^{\\pi/2} \\frac{\\sqrt{\\sin x}}{\\sqrt{\\sin x} + \\sqrt{\\cos x}} dx using King\'s symmetry property.',
};

/**
 * Normalizes escaped LaTeX delimiters to standard Markdown math delimiters:
 * \( ... \) -> $...$ (inline math)
 * \[ ... \] -> $$...$$ (block math)
 * Handles multiline equations reliably for remark-math and rehype-katex.
 */
export function preprocessLatex(text) {
  if (!text || typeof text !== 'string') return '';
  return text
    .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$')
    .replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
}

export default function ActiveMentorChat({ initialDoubt, initialSubject }) {
  const location = useLocation();
  const navigate = useNavigate();

  const {
    sessionId,
    connectionStatus,
    messages,
    currentHintLevel,
    isLoading,
    statusText,
    activeTopic,
    activeSubject,
    sendDoubt,
    sendTestHandoff,
    submitAttempt,
    requestNextHint,
    requestMasterSolution,
    loadHistoricalSession,
    resetSession,
  } = useMentorSocket();

  const [inputQuery, setInputQuery] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [subject, setSubject] = useState('Physics');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [studentAttempt, setStudentAttempt] = useState('');

  const chatBottomRef = useRef(null);
  const fileInputRef = useRef(null);
  const handoffSentRef = useRef(false);

  // Test Series -> Active Mentor handoff handler
  useEffect(() => {
    if (location.state?.handoff && !handoffSentRef.current) {
      if (connectionStatus === 'CONNECTED') {
        handoffSentRef.current = true;
        const handoffPayload = location.state;
        if (handoffPayload.subject) {
          setSubject(handoffPayload.subject);
        }
        sendTestHandoff(handoffPayload);
        navigate(location.pathname, { replace: true, state: {} });
        window.history.replaceState({}, '');
      }
    }
  }, [location.state, connectionStatus, sendTestHandoff, navigate, location.pathname]);

  // Sync initial doubt / subject when routed from Test Series or external modules
  useEffect(() => {
    if (initialDoubt) {
      setInputQuery(initialDoubt);
    }
    if (initialSubject) {
      setSubject(initialSubject);
    }
  }, [initialDoubt, initialSubject]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Image Upload and Canvas-based Downsampling (Max 800px width)
  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new window.Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxWidth = 800;
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        const resizedBase64 = canvas.toDataURL('image/jpeg', 0.85);
        setSelectedImage(resizedBase64);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // Dynamically passes current active subject pill state to the WebSocket payload
  const handleSend = (e) => {
    if (e) e.preventDefault();
    const textToSend = inputQuery.trim();
    if ((!textToSend && !selectedImage) || isLoading) return;

    sendDoubt(
      textToSend || 'Please review the attached problem diagram and question.',
      subject,
      selectedImage
    );

    setInputQuery('');
    setSelectedImage(null);
  };

  // Submit Student Attempt for Socratic Checkpoint Evaluation
  const handleAttemptSubmit = (e) => {
    if (e) e.preventDefault();
    if (isLoading || currentHintLevel >= 4) return;
    const attemptText = studentAttempt.trim();

    submitAttempt(attemptText || 'I am stuck', currentHintLevel);
    setStudentAttempt('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const loadSample = () => {
    setInputQuery(SAMPLE_QUESTIONS[subject]);
  };

  const handleSelectHistorySession = (historyData) => {
    loadHistoricalSession(historyData);
    if (historyData?.subject) {
      setSubject(historyData.subject);
    }
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  const isDoubtActive = messages.length > 0;

  return (
    <div className="flex h-[calc(100vh-8.5rem)] max-w-7xl mx-auto gap-4 overflow-hidden">
      {/* 1. Toggleable History Sidebar */}
      <HistorySidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((prev) => !prev)}
        onSelectSession={handleSelectHistorySession}
        activeSessionId={sessionId}
        onNewSession={resetSession}
      />

      {/* 2. Main Chat Panel */}
      <div className="flex-1 flex flex-col h-full space-y-3 overflow-hidden">
        {/* Header & Stepped Progress Bar */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-xl flex-shrink-0">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setIsSidebarOpen((prev) => !prev)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all"
                title="Toggle doubt history"
              >
                <History className="w-4 h-4" />
              </button>

              <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Zap className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-100">Active Mentor Socratic Session</h3>
                  <span className="text-[10px] text-slate-400 font-mono">#{sessionId.slice(0, 8)}</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  {activeTopic ? `Topic: ${activeTopic}` : `Subject: ${subject} • Socratic Progressive Mentoring`}
                </p>
              </div>
            </div>

            {/* Connection Status Badge */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-950 border border-slate-800">
                <span
                  className={`w-2 h-2 rounded-full ${
                    connectionStatus === 'CONNECTED'
                      ? 'bg-emerald-400 animate-pulse'
                      : connectionStatus === 'CONNECTING'
                      ? 'bg-amber-400 animate-ping'
                      : 'bg-rose-500'
                  }`}
                />
                <span className="text-[11px] text-slate-300 capitalize">{connectionStatus.toLowerCase()}</span>
              </div>

              {isDoubtActive && (
                <button
                  type="button"
                  onClick={resetSession}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>New Doubt</span>
                </button>
              )}
            </div>
          </div>

          {/* 4-Stage Stepped Progress Indicator */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80">
            {PROGRESS_STAGES.map((stage) => {
              const Icon = stage.icon;
              const isCompleted = currentHintLevel > stage.level;
              const isCurrent = currentHintLevel === stage.level;

              return (
                <div
                  key={stage.level}
                  className={`border rounded-xl px-3 py-2 flex items-center gap-2.5 transition-all ${
                    isCurrent
                      ? 'border-indigo-500 bg-indigo-950/40 ring-1 ring-indigo-500/40 shadow-sm'
                      : isCompleted
                      ? 'border-slate-700 bg-slate-950/70 text-slate-200'
                      : 'border-slate-800/60 bg-slate-950/30 text-slate-600 opacity-60'
                  }`}
                >
                  <div
                    className={`p-1.5 rounded-lg border text-xs font-bold ${
                      isCurrent
                        ? 'bg-indigo-600 text-white border-indigo-500'
                        : isCompleted
                        ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800'
                        : 'bg-slate-900 border-slate-800 text-slate-600'
                    }`}
                  >
                    {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                  </div>
                  <div className="overflow-hidden">
                    <div className="text-[11px] font-bold truncate text-slate-200">{stage.label}</div>
                    <div className="text-[9px] text-slate-400 uppercase font-semibold">
                      {isCurrent ? 'Active Level' : isCompleted ? 'Completed' : 'Locked'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Message Stream Feed */}
        <div className="flex-1 overflow-y-auto px-1 space-y-4 pr-1">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-900/40 border border-slate-800/80 rounded-3xl backdrop-blur-md">
              <div className="w-14 h-14 rounded-3xl bg-gradient-to-br from-indigo-500 via-purple-500 to-blue-500 flex items-center justify-center shadow-xl shadow-indigo-500/20 mb-4">
                <Sparkles className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-lg font-bold text-slate-100 mb-1">Ready for JEE Doubt Resolution</h3>
              <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
                Submit your question or attach a problem diagram to unlock the 3-Tier Progressive Hint engine. We guide your problem setup and intermediate algebra without revealing final spoilers early.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-2">
                {['Physics', 'Chemistry', 'Mathematics'].map((sub) => (
                  <button
                    key={sub}
                    type="button"
                    onClick={() => {
                      setSubject(sub);
                      setInputQuery(SAMPLE_QUESTIONS[sub]);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-indigo-300 bg-indigo-950/40 hover:bg-indigo-950/70 border border-indigo-800/50 shadow-sm transition-all"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Try {sub} Sample
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={{
                  ...msg,
                  content: preprocessLatex(msg.content),
                }}
              />
            ))
          )}

          {/* Speculative Loading Skeleton */}
          {isLoading && (
            <div className="w-full flex justify-start my-3">
              <div className="max-w-xl w-full bg-slate-900/90 border border-indigo-500/40 rounded-2xl p-5 shadow-xl backdrop-blur-md space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-indigo-500/30 border-t-indigo-400 rounded-full animate-spin flex-shrink-0" />
                  <span className="text-xs font-semibold text-indigo-300 animate-pulse">{statusText}</span>
                </div>
                <div className="space-y-2 pt-1">
                  <div className="h-3 bg-slate-800/70 rounded-full w-4/5 animate-pulse" />
                  <div className="h-3 bg-slate-800/50 rounded-full w-3/5 animate-pulse" />
                </div>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Active Socratic Checkpoint Evaluation Panel */}
        {isDoubtActive && currentHintLevel < 4 && (
          <div className="bg-slate-900/95 border border-indigo-500/40 rounded-2xl p-3.5 shadow-xl backdrop-blur-md flex-shrink-0 space-y-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-slate-200">
                  Socratic Checkpoint • Tier {currentHintLevel} Evaluation
                </span>
              </div>
              <span className="text-[10px] text-slate-400 hidden sm:inline">
                Attempt your next step or ask for progressive guidance
              </span>
            </div>

            {/* Checkpoint Attempt Submission Form */}
            <form onSubmit={handleAttemptSubmit} className="flex flex-wrap sm:flex-nowrap items-center gap-2">
              <input
                type="text"
                value={studentAttempt}
                onChange={(e) => setStudentAttempt(e.target.value)}
                placeholder="Type your answer or next step here... (or 'I am stuck')"
                disabled={isLoading}
                className="flex-1 min-w-[200px] bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              />

              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="inline-flex items-center gap-1.5 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-bold px-3.5 py-2.5 rounded-xl shadow-md shadow-indigo-500/20 transition-all"
                >
                  <span>Check Step</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    submitAttempt('I am stuck', currentHintLevel);
                    setStudentAttempt('');
                  }}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 hover:text-white text-xs font-semibold px-3 py-2.5 rounded-xl border border-slate-700 transition-all"
                  title="Request next hint tier directly"
                >
                  <span>I am stuck</span>
                </button>

                <button
                  type="button"
                  onClick={requestMasterSolution}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 bg-purple-950/70 hover:bg-purple-900 border border-purple-700/60 disabled:opacity-50 text-purple-200 text-xs font-bold px-3 py-2.5 rounded-xl transition-all"
                  title="Reveal master solution"
                >
                  <Award className="w-3.5 h-3.5 text-purple-400" />
                  <span className="hidden sm:inline">Solution</span>
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Input Area with Dynamic Subject Sync & Image Attachment */}
        <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-4 shadow-2xl backdrop-blur-xl flex-shrink-0">
          <div className="flex items-center justify-between gap-2 mb-2.5">
            {/* Subject Toggle Pills */}
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
              {['Physics', 'Chemistry', 'Mathematics'].map((sub) => (
                <button
                  key={sub}
                  type="button"
                  onClick={() => setSubject(sub)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    subject === sub
                      ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sub}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={loadSample}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 transition-all"
            >
              Paste {subject} sample
            </button>
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleImageSelect}
          />

          {/* Image Attachment Preview Thumbnail */}
          {selectedImage && (
            <div className="relative inline-block mb-3">
              <div className="relative rounded-xl overflow-hidden border border-indigo-500/50 shadow-lg bg-slate-950 max-w-[180px]">
                <img
                  src={selectedImage}
                  alt="Selected doubt attachment"
                  className="h-20 w-auto object-cover rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => setSelectedImage(null)}
                  className="absolute top-1 right-1 p-1 rounded-full bg-slate-900/90 text-slate-300 hover:text-white hover:bg-rose-600 transition-all shadow-md"
                  title="Remove image"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <span className="text-[10px] text-indigo-400 font-medium mt-1 block">Image attached (resized max 800px)</span>
            </div>
          )}

          <form onSubmit={handleSend} className="relative flex items-center gap-2">
            {/* Attachment Paperclip Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className={`h-12 w-12 flex-shrink-0 rounded-xl flex items-center justify-center border transition-all ${
                selectedImage
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-sm shadow-indigo-500/20'
                  : 'bg-slate-950 hover:bg-slate-800 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
              title="Attach problem screenshot or diagram"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <textarea
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedImage
                  ? `Describe your ${subject} doubt regarding the attached diagram...`
                  : `Ask any ${subject} doubt with LaTeX equations ($...$ inline, $$...$$ block)...`
              }
              rows={2}
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-3.5 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 resize-none"
            />

            <button
              type="submit"
              disabled={isLoading || (!inputQuery.trim() && !selectedImage)}
              className="h-12 w-12 flex-shrink-0 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center shadow-lg shadow-indigo-600/30 transition-all"
              title={`Send ${subject} doubt to mentor`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
