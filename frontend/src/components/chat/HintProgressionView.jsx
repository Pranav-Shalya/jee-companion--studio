import React, { useState } from 'react';
import {
  Lightbulb,
  GitBranch,
  CheckCircle2,
  Lock,
  ArrowRight,
  Send,
  AlertTriangle,
  HelpCircle,
  Sparkles,
} from 'lucide-react';
import LatexRenderer from './LatexRenderer';

const TIER_CONFIG = [
  {
    tier: 1,
    title: 'Tier 1: Conceptual Nudge',
    subtitle: 'Core Laws, Governing Principles & Formulations',
    icon: Lightbulb,
    color: 'border-indigo-500/40 bg-indigo-950/20 text-indigo-400',
    badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  },
  {
    tier: 2,
    title: 'Tier 2: Structural Strategy',
    subtitle: 'Step-by-Step Equation Setup & Problem Roadmap',
    icon: GitBranch,
    color: 'border-blue-500/40 bg-blue-950/20 text-blue-400',
    badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
  {
    tier: 3,
    title: 'Tier 3: Detailed Walkthrough',
    subtitle: 'Intermediate Algebraic Evaluation (Student Evaluates Final Step)',
    icon: CheckCircle2,
    color: 'border-emerald-500/40 bg-emerald-950/20 text-emerald-400',
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  },
];

export default function HintProgressionView({
  session,
  onRequestNextTier,
  onSubmitAttempt,
  isLoadingTier,
  isEvaluatingAttempt,
  attemptFeedback,
}) {
  const [studentAttempt, setStudentAttempt] = useState('');

  if (!session) return null;

  const currentTier = session.current_tier || 1;
  const hints = session.hints_history || [];

  const handleAttemptSubmit = (e) => {
    e.preventDefault();
    if (!studentAttempt.trim()) return;
    onSubmitAttempt(studentAttempt);
  };

  return (
    <div className="space-y-6">
      {/* Problem Recap Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4.5 backdrop-blur-md">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {session.subject}
            </span>
            <span className="text-xs text-slate-400">Session: #{session.session_id}</span>
          </div>
          <span className="text-xs font-medium text-indigo-400 bg-indigo-950/50 border border-indigo-800/40 px-2.5 py-0.5 rounded-full">
            Tier {currentTier} / 3 Active
          </span>
        </div>
        <div className="text-sm text-slate-200 font-medium">
          <LatexRenderer content={session.extracted_query} />
        </div>
      </div>

      {/* 3-Tier Stepper Progress Bar */}
      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        {TIER_CONFIG.map((tierConfig) => {
          const Icon = tierConfig.icon;
          const isUnlocked = currentTier >= tierConfig.tier;
          const isCurrent = currentTier === tierConfig.tier;

          return (
            <div
              key={tierConfig.tier}
              className={`border rounded-xl p-3 transition-all ${
                isCurrent
                  ? 'border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/50'
                  : isUnlocked
                  ? 'border-slate-700 bg-slate-900/50 text-slate-300'
                  : 'border-slate-800/60 bg-slate-950/40 text-slate-600 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`p-1.5 rounded-lg border text-xs font-semibold ${
                    isUnlocked ? tierConfig.badge : 'bg-slate-800 border-slate-700 text-slate-500'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-semibold">Tier {tierConfig.tier}</span>
                {!isUnlocked && <Lock className="w-3 h-3 ml-auto text-slate-600" />}
              </div>
              <p className="text-[11px] truncate text-slate-400 font-medium">{tierConfig.title.split(': ')[1]}</p>
            </div>
          );
        })}
      </div>

      {/* Unlocked Hint Cards */}
      <div className="space-y-4">
        {hints.map((hint, idx) => {
          const config = TIER_CONFIG.find((c) => c.tier === hint.tier) || TIER_CONFIG[0];
          const Icon = config.icon;

          return (
            <div
              key={idx}
              className={`border rounded-2xl p-5 shadow-xl transition-all ${config.color} border-opacity-60 backdrop-blur-md`}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-xl border ${config.badge}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">{hint.tier_name || config.title}</h3>
                    <p className="text-xs text-slate-400">{config.subtitle}</p>
                  </div>
                </div>
                <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${config.badge}`}>
                  Tier {hint.tier}
                </span>
              </div>

              {/* Concept Summary */}
              <div className="mb-4 bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5">
                <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <Lightbulb className="w-3.5 h-3.5" /> Core Concept & Principles
                </h4>
                <div className="text-xs text-slate-300 leading-relaxed">
                  <LatexRenderer content={hint.concept_summary} />
                </div>
              </div>

              {/* Governing Formulas */}
              {hint.governing_formulas && hint.governing_formulas.length > 0 && (
                <div className="mb-4 bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5">
                  <h4 className="text-xs font-semibold text-blue-300 uppercase tracking-wider mb-2">
                    Governing Equations & Formulas
                  </h4>
                  <div className="space-y-1.5">
                    {hint.governing_formulas.map((form, fIdx) => (
                      <div key={fIdx} className="bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
                        <LatexRenderer content={`$$${form}$$`} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hint Content / Step Guidance */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Pedagogical Guidance
                </h4>
                <div className="text-xs text-slate-200 leading-relaxed bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                  <LatexRenderer content={hint.hint_content} />
                </div>
              </div>

              {/* Probing Reflective Question */}
              {hint.probing_question && (
                <div className="mb-3 bg-amber-950/20 border border-amber-800/40 rounded-xl p-3 flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-[11px] font-semibold uppercase text-amber-400 tracking-wider">
                      Think About This:
                    </h5>
                    <p className="text-xs text-amber-200/90 mt-0.5">
                      {hint.probing_question}
                    </p>
                  </div>
                </div>
              )}

              {/* Pitfall Warning */}
              {hint.pitfall_warning && (
                <div className="bg-rose-950/20 border border-rose-800/40 rounded-xl p-3 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h5 className="text-[11px] font-semibold uppercase text-rose-400 tracking-wider">
                      JEE Trap Warning:
                    </h5>
                    <p className="text-xs text-rose-200/90 mt-0.5">
                      {hint.pitfall_warning}
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Student Interactive Workspace / Step Submission */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl">
        <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2 mb-1">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          Test Your Step / Submit Partial Attempt
        </h4>
        <p className="text-xs text-slate-400 mb-3">
          Type your intermediate equation or deduction. The AI tutor evaluates your direction without spoiling the answer.
        </p>

        <form onSubmit={handleAttemptSubmit} className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={studentAttempt}
              onChange={(e) => setStudentAttempt(e.target.value)}
              placeholder="e.g., I found Δv = 2v and Δt = πR/v. Is my ratio correct?"
              className="flex-1 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
            <button
              type="submit"
              disabled={isEvaluatingAttempt || !studentAttempt.trim()}
              className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-medium px-4 py-2.5 rounded-xl border border-slate-700 transition-all"
            >
              {isEvaluatingAttempt ? (
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Verify Step</span>
                  <Send className="w-3 h-3" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Socratic Feedback Alert */}
        {attemptFeedback && (
          <div
            className={`mt-4 p-4 rounded-xl border transition-all ${
              attemptFeedback.is_on_track
                ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
                : 'bg-amber-950/30 border-amber-800/60 text-amber-200'
            }`}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider">
                {attemptFeedback.is_on_track ? '✅ On the Right Track' : '⚠️ Need Adjustment'}
              </span>
            </div>
            <p className="text-xs font-medium mb-1">{attemptFeedback.feedback}</p>
            <p className="text-xs opacity-90 italic">💡 {attemptFeedback.socratic_guidance}</p>
          </div>
        )}

        {/* Unlock Next Hint Tier Button */}
        {currentTier < 3 && (
          <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-400">
              Need more structural help? Unlock Tier {currentTier + 1}.
            </span>
            <button
              type="button"
              onClick={() => onRequestNextTier(currentTier + 1)}
              disabled={isLoadingTier}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-md shadow-indigo-500/20 transition-all"
            >
              {isLoadingTier ? (
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Unlock Tier {currentTier + 1} Hint</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
