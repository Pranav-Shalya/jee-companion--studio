import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import {
  Play,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ArrowLeft,
  ArrowRight,
  HelpCircle,
  Award,
  Sparkles,
  Clock,
  Flame,
  BookOpen,
  Atom,
  FlaskConical,
  Calculator,
  AlertTriangle,
  Check,
  ChevronRight,
  GraduationCap,
  FileCheck2,
  Layers,
  Send,
  Cpu,
} from 'lucide-react';

function preprocessLatex(text) {
  if (!text || typeof text !== 'string') return '';
  return text
    .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$')
    .replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
}

function parseOptionsSafely(optionsJson) {
  if (!optionsJson) return [];
  if (Array.isArray(optionsJson)) return optionsJson;
  if (typeof optionsJson === 'string') {
    try {
      const parsed = JSON.parse(optionsJson);
      if (Array.isArray(parsed)) return parsed;
      return [parsed];
    } catch (err) {
      console.warn('Could not parse options_json:', err);
      return [];
    }
  }
  return [];
}

const SUBJECT_THEMES = {
  Physics: {
    icon: Atom,
    border: 'border-indigo-500/40',
    bg: 'bg-indigo-950/30',
    badge: 'text-indigo-400 bg-indigo-950/60 border-indigo-500/30',
    accent: 'from-indigo-600 to-blue-600',
  },
  Chemistry: {
    icon: FlaskConical,
    border: 'border-emerald-500/40',
    bg: 'bg-emerald-950/30',
    badge: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
    accent: 'from-emerald-600 to-teal-600',
  },
  Mathematics: {
    icon: Calculator,
    border: 'border-purple-500/40',
    bg: 'bg-purple-950/30',
    badge: 'text-purple-400 bg-purple-950/60 border-purple-500/30',
    accent: 'from-purple-600 to-pink-600',
  },
};

const SAMPLE_TOPICS = {
  Physics: ['Rotational Dynamics', 'Work-Energy Theorem', 'Thermodynamics', 'Electrostatics'],
  Chemistry: ['Chemical Equilibrium', 'SN2 Mechanisms', 'Coordination Compounds', 'Thermodynamics'],
  Mathematics: ['Integration by Parts', 'Definite Integrals', 'Vectors & 3D', 'Conic Sections'],
};

export default function TestSeriesInterface({ onResolveWithMentor }) {
  const navigate = useNavigate();
  const { userId, getToken } = useAuth();

  // Test Configuration State
  const [testConfig, setTestConfig] = useState({
    subject: 'Physics',
    topic: 'Rotational Dynamics',
    count: 5,
    examType: 'JEE Mains', // 'JEE Mains' | 'JEE Advanced'
  });

  // Test Lifecycle: 'idle' | 'loading' | 'active' | 'finished'
  const [testState, setTestState] = useState('idle');
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [studentAnswers, setStudentAnswers] = useState({});
  const [errorMsg, setErrorMsg] = useState(null);
  const [timeSpentSeconds, setTimeSpentSeconds] = useState(0);

  // Timer for active test session
  useEffect(() => {
    let interval;
    if (testState === 'active') {
      interval = setInterval(() => {
        setTimeSpentSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [testState]);

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // API Integration: Fetch Test Questions from Backend with Hybrid RAG + LLM Strategy
  const startTest = async () => {
    setTestState('loading');
    setErrorMsg(null);
    setTimeSpentSeconds(0);

    const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
    const apiUrl = `${apiBaseUrl}/api/v1/tests/generate`;

    try {
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: testConfig.subject,
          topic: testConfig.topic.trim() || undefined,
          count: parseInt(testConfig.count, 10) || 5,
          difficulty: testConfig.examType,
          exam_type: testConfig.examType,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${res.status}`);
      }

      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        throw new Error('No test questions returned. Please try again or adjust your topic.');
      }

      setQuestions(data);
      setCurrentQuestionIndex(0);
      setStudentAnswers({});
      setTestState('active');
    } catch (err) {
      console.error('❌ [TEST-SERIES] Error generating test:', err);
      setErrorMsg(err.message || 'Could not generate test series paper.');
      setTestState('idle');
    }
  };

  const handleSelectOption = (questionIdx, optionKey) => {
    setStudentAnswers((prev) => ({
      ...prev,
      [questionIdx]: prev[questionIdx] === optionKey ? null : optionKey,
    }));
  };

  const handleFinishTest = async () => {
    setTestState('finished');

    // Calculate final score percentage
    let correct = 0;
    const total = questions.length || 1;

    questions.forEach((q, idx) => {
      const studentAns = studentAnswers[idx];
      const expected = q.correct_option || 'A';
      if (studentAns === expected) {
        correct += 1;
      }
    });

    const finalScorePercentage = Math.round((correct / total) * 100);

    // Send analytics telemetry for Ebbinghaus forgetting curve tracking
    try {
      let token = null;
      try {
        if (getToken) {
          token = await getToken();
        }
      } catch (tokenErr) {
        console.warn('Could not retrieve Clerk auth token:', tokenErr);
      }

      const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
      const logUrl = `${apiBaseUrl}/api/v1/analytics/log`;
      const difficultyVal = testConfig.examType === 'JEE Advanced' ? 1.2 : 1.0;

      const headers = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      await fetch(logUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          user_id: userId || 'default_user',
          subject: testConfig.subject,
          topic: testConfig.topic,
          score: finalScorePercentage,
          difficulty: difficultyVal,
        }),
      });
    } catch (err) {
      console.warn('⚠️ [ANALYTICS] Failed to log telemetry (offline):', err);
    }
  };

  const handleResetTest = () => {
    setTestState('idle');
    setQuestions([]);
    setStudentAnswers({});
    setCurrentQuestionIndex(0);
    setTimeSpentSeconds(0);
  };

  // Score Calculation
  const calculateResults = () => {
    let attempted = 0;
    let correct = 0;
    let incorrect = 0;

    questions.forEach((q, idx) => {
      const studentAns = studentAnswers[idx];
      if (studentAns) {
        attempted += 1;
        const expected = q.correct_option || 'A';
        if (studentAns === expected) {
          correct += 1;
        } else {
          incorrect += 1;
        }
      }
    });

    const unattempted = questions.length - attempted;
    const totalScore = correct * 4 - incorrect * 1;
    const maxScore = questions.length * 4;
    const accuracy = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;

    return { attempted, correct, incorrect, unattempted, totalScore, maxScore, accuracy };
  };

  const isQuestionPYQ = (q) => {
    if (!q) return false;
    return q.content_type === 'pyq' || (q.doc_id && !q.doc_id.startsWith('gen-') && q.content_type !== 'generated_mcq');
  };

  const currentQ = questions[currentQuestionIndex];
  const subjectTheme = SUBJECT_THEMES[testConfig.subject] || SUBJECT_THEMES.Physics;
  const SubjectIcon = subjectTheme.icon;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Test Series Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <GraduationCap className="w-3.5 h-3.5" />
            <span>Targeted JEE Test Series &amp; PYQ Simulator</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            JEE Mock Test Engine
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300">
              Hybrid RAG + LLM
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Simulate real exam pressure with vector-curated JEE Main &amp; Advanced mock papers, instant scoring, step derivations, and seamless Socratic mentor resolution.
          </p>
        </div>

        {testState === 'active' && (
          <div className="flex items-center gap-3 bg-slate-950/90 border border-slate-800 px-4 py-2 rounded-2xl">
            <Clock className="w-4 h-4 text-indigo-400 animate-pulse" />
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Time Elapsed</span>
              <span className="text-sm font-mono font-bold text-slate-200">{formatTimer(timeSpentSeconds)}</span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Configuration State: IDLE / CONFIG */}
      {testState === 'idle' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-6">
          <div className="flex items-center gap-2.5 pb-4 border-b border-slate-800">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Configure Your Practice Test Paper
            </h3>
          </div>

          {errorMsg && (
            <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-3">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Subject Selector */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Subject</label>
              <div className="grid grid-cols-3 gap-2">
                {['Physics', 'Chemistry', 'Mathematics'].map((sub) => {
                  const isSel = testConfig.subject === sub;
                  return (
                    <button
                      key={sub}
                      type="button"
                      onClick={() => setTestConfig((prev) => ({ ...prev, subject: sub, topic: SAMPLE_TOPICS[sub][0] }))}
                      className={`p-3 rounded-2xl border text-xs font-bold transition-all text-center ${
                        isSel
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/30'
                          : 'bg-slate-950/60 hover:bg-slate-800 text-slate-400 border-slate-800'
                      }`}
                    >
                      {sub}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Exam Type Toggle (JEE Mains vs JEE Advanced) */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Exam Type Target
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'JEE Mains', label: 'JEE Mains' },
                  { id: 'JEE Advanced', label: 'JEE Advanced' },
                ].map((item) => {
                  const isSel = testConfig.examType === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setTestConfig((prev) => ({ ...prev, examType: item.id }))}
                      className={`p-3 rounded-2xl border text-xs font-bold transition-all text-center flex items-center justify-center gap-2 ${
                        isSel
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/30'
                          : 'bg-slate-950/60 hover:bg-slate-800 text-slate-400 border-slate-800'
                      }`}
                    >
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Topic Input & Quick Suggestions */}
            <div className="space-y-2 sm:col-span-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Topic / Chapter Focus</label>
              <input
                type="text"
                value={testConfig.topic}
                onChange={(e) => setTestConfig((prev) => ({ ...prev, topic: e.target.value }))}
                placeholder="e.g. Rotational Dynamics, Integration by Parts..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-3.5 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              />

              {/* Sample Topic Pills */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[10px] text-slate-500 uppercase font-semibold mr-1">Popular:</span>
                {(SAMPLE_TOPICS[testConfig.subject] || []).map((top) => (
                  <button
                    key={top}
                    type="button"
                    onClick={() => setTestConfig((prev) => ({ ...prev, topic: top }))}
                    className="text-[11px] px-2.5 py-1 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
                  >
                    {top}
                  </button>
                ))}
              </div>
            </div>

            {/* Question Count */}
            <div className="space-y-2 sm:col-span-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Question Count: <span className="text-indigo-400 font-mono">{testConfig.count} Questions</span>
              </label>
              <input
                type="range"
                min="2"
                max="10"
                step="1"
                value={testConfig.count}
                onChange={(e) => setTestConfig((prev) => ({ ...prev, count: parseInt(e.target.value, 10) }))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>2 Questions (Quick Mock)</span>
                <span>5 Questions (Standard)</span>
                <span>10 Questions (Full Sprint)</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="button"
              onClick={startTest}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs sm:text-sm font-bold px-6 py-3 rounded-2xl shadow-xl shadow-indigo-600/30 transition-all"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Launch Practice Test ({testConfig.examType})</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Loading State */}
      {testState === 'loading' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-12 text-center backdrop-blur-xl shadow-2xl space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto shadow-xl animate-pulse">
            <Sparkles className="w-7 h-7 text-white animate-spin" />
          </div>
          <h3 className="text-base font-bold text-slate-100">Curating Hybrid Test Paper ({testConfig.examType})...</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Retrieving vector points from <span className="text-indigo-300 font-mono">jee_test_series</span> and synthesizing dynamic {testConfig.examType} MCQs via LLM consensus for {testConfig.subject}.
          </p>
        </div>
      )}

      {/* 4. Active Test Interface */}
      {testState === 'active' && currentQ && (
        <div className="space-y-4">
          {/* Question Navigator Palette */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 backdrop-blur-xl flex flex-wrap items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-slate-300 uppercase">
                Question {currentQuestionIndex + 1} of {questions.length}
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${subjectTheme.badge}`}>
                {currentQ.topic || testConfig.topic}
              </span>

              {/* Source Badge: PYQ vs AI Generated */}
              {isQuestionPYQ(currentQ) ? (
                <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300">
                  <Award className="w-3 h-3 text-amber-400" />
                  <span>PYQ Archive</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-300">
                  <Sparkles className="w-3 h-3 text-purple-400" />
                  <span>AI Generated</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              {questions.map((_, qIdx) => {
                const isCurrent = qIdx === currentQuestionIndex;
                const isAnswered = studentAnswers[qIdx] !== undefined && studentAnswers[qIdx] !== null;

                return (
                  <button
                    key={qIdx}
                    type="button"
                    onClick={() => setCurrentQuestionIndex(qIdx)}
                    className={`w-8 h-8 rounded-xl text-xs font-mono font-bold transition-all border ${
                      isCurrent
                        ? 'bg-indigo-600 text-white border-indigo-400 shadow-md shadow-indigo-600/40 ring-1 ring-indigo-400'
                        : isAnswered
                        ? 'bg-emerald-950/80 text-emerald-400 border-emerald-700'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {qIdx + 1}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question Statement Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6 min-h-[380px]">
            <div className="prose prose-invert max-w-none text-xs sm:text-sm text-slate-200 leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                {preprocessLatex(currentQ.text)}
              </ReactMarkdown>
            </div>

            {/* Multiple Choice Options */}
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                Select Your Answer Choice:
              </span>

              {(() => {
                const parsedOptions = typeof currentQ.options_json === 'string'
                  ? (() => { try { return JSON.parse(currentQ.options_json); } catch (e) { return []; } })()
                  : (Array.isArray(currentQ.options_json) ? currentQ.options_json : parseOptionsSafely(currentQ.options_json || currentQ.options));

                return (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {['A', 'B', 'C', 'D'].map((opt, oIdx) => {
                      const isSelected = studentAnswers[currentQuestionIndex] === opt;
                      const optText = parsedOptions && parsedOptions[oIdx];

                      return (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => handleSelectOption(currentQuestionIndex, opt)}
                          className={`text-left p-4 rounded-2xl border transition-all flex items-start gap-3.5 ${
                            isSelected
                              ? 'bg-indigo-950/70 border-indigo-500 text-slate-100 shadow-lg shadow-indigo-950/50 ring-1 ring-indigo-500/50'
                              : 'bg-slate-950/60 hover:bg-slate-800/80 border-slate-800/80 text-slate-300 hover:border-slate-700'
                          }`}
                        >
                          <div
                            className={`w-7 h-7 rounded-xl flex-shrink-0 flex items-center justify-center font-mono font-bold text-xs border mt-0.5 ${
                              isSelected
                                ? 'bg-indigo-600 text-white border-indigo-400'
                                : 'bg-slate-900 text-slate-400 border-slate-800'
                            }`}
                          >
                            {opt}
                          </div>
                          <div className="flex-1 text-xs font-medium text-slate-200">
                            {optText ? (
                              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                                {preprocessLatex(optText)}
                              </ReactMarkdown>
                            ) : (
                              <span>Option ({opt})</span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

            {/* Navigation & Submission Controls */}
            <div className="pt-6 border-t border-slate-800 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setCurrentQuestionIndex((prev) => Math.max(0, prev - 1))}
                disabled={currentQuestionIndex === 0}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs font-bold text-slate-300 transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Previous</span>
              </button>

              <div className="flex items-center gap-2">
                {currentQuestionIndex < questions.length - 1 ? (
                  <button
                    type="button"
                    onClick={() => setCurrentQuestionIndex((prev) => Math.min(questions.length - 1, prev + 1))}
                    className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-md shadow-indigo-600/30 transition-all"
                  >
                    <span>Next Question</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleFinishTest}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-extrabold text-white shadow-lg shadow-emerald-600/30 transition-all"
                  >
                    <FileCheck2 className="w-4 h-4" />
                    <span>Submit &amp; Grade Test</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Results & Graded Solutions Interface */}
      {testState === 'finished' && (
        <div className="space-y-6">
          {/* Score Overview Card */}
          {(() => {
            const stats = calculateResults();
            return (
              <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
                <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
                  <div>
                    <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                      {testConfig.examType} Test Completed
                    </span>
                    <h3 className="text-xl font-extrabold text-slate-100 mt-0.5">
                      Performance Summary &amp; KaTeX Solutions
                    </h3>
                  </div>

                  <button
                    type="button"
                    onClick={handleResetTest}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 transition-all"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Take Another Test</span>
                  </button>
                </div>

                {/* Score Stats Matrix */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6">
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Score</span>
                    <span className="text-xl font-extrabold text-indigo-400">
                      {stats.totalScore} / {stats.maxScore}
                    </span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Accuracy</span>
                    <span className="text-xl font-extrabold text-emerald-400">{stats.accuracy}%</span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Correct / Attempted</span>
                    <span className="text-xl font-extrabold text-slate-200">
                      {stats.correct} / {stats.attempted}
                    </span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Time Spent</span>
                    <span className="text-xl font-extrabold text-slate-200 font-mono">{formatTimer(timeSpentSeconds)}</span>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Graded Question Breakdown List */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Detailed Question Analysis &amp; Mathematical Derivations:
            </h4>

            {questions.map((q, idx) => {
              const studentAns = studentAnswers[idx];
              const expectedAns = q.correct_option || 'A';
              const isCorrect = studentAns === expectedAns;
              const wasAttempted = Boolean(studentAns);
              const isPyq = isQuestionPYQ(q);

              return (
                <div
                  key={idx}
                  className={`bg-slate-900/80 border rounded-3xl p-6 backdrop-blur-xl shadow-xl space-y-4 ${
                    isCorrect
                      ? 'border-emerald-500/40'
                      : wasAttempted
                      ? 'border-rose-500/40'
                      : 'border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-300">#{idx + 1}</span>
                      <span className="text-xs font-semibold text-slate-200">{q.topic || 'JEE Practice'}</span>

                      {/* PYQ vs AI Generated Badge */}
                      {isPyq ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300">
                          <Award className="w-3 h-3 text-amber-400" />
                          <span>PYQ Archive</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/40 text-purple-300">
                          <Sparkles className="w-3 h-3 text-purple-400" />
                          <span>AI Generated</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {isCorrect ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-950/50 border border-emerald-800/60 px-2.5 py-1 rounded-xl">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Correct (+4) [Selected: {studentAns}]</span>
                        </span>
                      ) : wasAttempted ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-400 bg-rose-950/50 border border-rose-800/60 px-2.5 py-1 rounded-xl">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Incorrect (-1) [Selected: {studentAns}, Correct: {expectedAns}]</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-800/50 border border-slate-700 px-2.5 py-1 rounded-xl">
                          <span>Unattempted (0) [Correct: {expectedAns}]</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Question Content */}
                  <div className="prose prose-invert max-w-none text-xs sm:text-sm text-slate-300">
                    <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {preprocessLatex(q.text)}
                    </ReactMarkdown>
                  </div>

                  {/* Options list in result */}
                  {(() => {
                    const parsedOptions = typeof q.options_json === 'string'
                      ? (() => { try { return JSON.parse(q.options_json); } catch (e) { return []; } })()
                      : (Array.isArray(q.options_json) ? q.options_json : parseOptionsSafely(q.options_json || q.options));

                    if (!parsedOptions || !Array.isArray(parsedOptions) || parsedOptions.length === 0) return null;

                    return (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                        {['A', 'B', 'C', 'D'].map((optKey, oIdx) => {
                          const optText = parsedOptions[oIdx];
                          if (!optText) return null;
                          const isExpected = optKey === expectedAns;
                          const isSelected = optKey === studentAns;

                          return (
                            <div
                              key={optKey}
                              className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 ${
                                isExpected
                                  ? 'bg-emerald-950/40 border-emerald-600/70 text-emerald-300'
                                  : isSelected
                                  ? 'bg-rose-950/40 border-rose-600/70 text-rose-300'
                                  : 'bg-slate-950/40 border-slate-800 text-slate-400'
                              }`}
                            >
                              <span className="font-mono font-bold">{optKey}:</span>
                              <div className="flex-1">
                                <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                                  {preprocessLatex(optText)}
                                </ReactMarkdown>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}

                  {/* Step-by-Step Mathematical Solution */}
                  {q.solution_latex && (
                    <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 space-y-2">
                      <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>Step-by-Step KaTeX Solution:</span>
                      </div>
                      <div className="prose prose-invert max-w-none text-xs sm:text-sm text-slate-200 leading-relaxed">
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {preprocessLatex(q.solution_latex)}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}

                  {/* Formulas & Pitfalls breakdown */}
                  {q.formulas && q.formulas.length > 0 && (
                    <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block">
                        Governing Equations &amp; Formulas:
                      </span>
                      <div className="space-y-1">
                        {q.formulas.map((form, fIdx) => (
                          <div key={fIdx} className="text-xs text-slate-300 font-mono">
                            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                              {preprocessLatex(`$${form}$`)}
                            </ReactMarkdown>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resolve with Active Mentor CTA */}
                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => {
                        const currentQuestionText = q.question_text || q.text || '';
                        const currentStudentOption = studentAnswers[idx] || studentAns || null;
                        const currentCorrectOption = q.correct_option || expectedAns || 'A';
                        const currentSolution = q.solution_latex || '';
                        const currentSubject = q.subject || testConfig.subject || 'Physics';

                        navigate('/chat', {
                          state: {
                            handoff: true,
                            question_text: currentQuestionText,
                            student_option: currentStudentOption,
                            correct_option: currentCorrectOption,
                            solution_latex: currentSolution,
                            subject: currentSubject,
                          },
                        });
                        if (onResolveWithMentor) {
                          onResolveWithMentor(currentQuestionText, currentSubject);
                        }
                      }}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 hover:text-white border border-indigo-500/40 shadow-sm transition-all"
                      title="Open this question in the Active Mentor progressive hint chat"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Resolve with Active Mentor</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
