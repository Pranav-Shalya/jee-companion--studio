import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Routes, Route } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton } from '@clerk/clerk-react';
import {
  Flame,
  Sparkles,
  BrainCircuit,
  Layers,
  ArrowRight,
  ShieldCheck,
  BookOpen,
} from 'lucide-react';
import Navbar from './components/Navbar';
import ActiveMentorChat from './components/chat/ActiveMentorChat';
import CompanionStudio from './components/studio/CompanionStudio';
import TestSeriesInterface from './components/test_series/TestSeriesInterface';
import AnalyticsDashboard from './components/dashboard/AnalyticsDashboard';

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active tab from route pathname or fallback
  const getTabFromPath = (path) => {
    if (path.startsWith('/test_series') || path.startsWith('/tests')) return 'test_series';
    if (path.startsWith('/dashboard') || path.startsWith('/analytics')) return 'dashboard';
    if (path.startsWith('/studio')) return 'studio';
    return 'chat';
  };

  const [activeTab, setActiveTab] = useState(() => getTabFromPath(location.pathname));
  const [mentorInitialDoubt, setMentorInitialDoubt] = useState(null);
  const [mentorInitialSubject, setMentorInitialSubject] = useState(null);

  useEffect(() => {
    const currentTab = getTabFromPath(location.pathname);
    setActiveTab(currentTab);
  }, [location.pathname]);

  const handleTabChange = (tabKey) => {
    setActiveTab(tabKey);
    const targetPath = tabKey === 'chat' ? '/chat' : `/${tabKey}`;
    if (location.pathname !== targetPath) {
      navigate(targetPath);
    }
  };

  const handleResolveWithMentor = (questionText, subject) => {
    setMentorInitialDoubt(questionText);
    setMentorInitialSubject(subject || 'Physics');
    handleTabChange('chat');
  };

  const handleStartReviewTest = (subject, topic) => {
    handleTabChange('test_series');
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      <Navbar activeTab={activeTab} onTabChange={handleTabChange} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Protected Authenticated View */}
        <SignedIn>
          <Routes>
            <Route
              path="/chat"
              element={
                <ActiveMentorChat
                  initialDoubt={mentorInitialDoubt}
                  initialSubject={mentorInitialSubject}
                />
              }
            />
            <Route
              path="/test_series"
              element={<TestSeriesInterface onResolveWithMentor={handleResolveWithMentor} />}
            />
            <Route
              path="/dashboard"
              element={<AnalyticsDashboard onNavigateToTest={handleStartReviewTest} />}
            />
            <Route
              path="/analytics"
              element={<AnalyticsDashboard onNavigateToTest={handleStartReviewTest} />}
            />
            <Route path="/studio" element={<CompanionStudio />} />
            <Route
              path="*"
              element={
                <>
                  {activeTab === 'chat' && (
                    <ActiveMentorChat
                      initialDoubt={mentorInitialDoubt}
                      initialSubject={mentorInitialSubject}
                    />
                  )}
                  {activeTab === 'test_series' && (
                    <TestSeriesInterface onResolveWithMentor={handleResolveWithMentor} />
                  )}
                  {activeTab === 'dashboard' && (
                    <AnalyticsDashboard onNavigateToTest={handleStartReviewTest} />
                  )}
                  {activeTab === 'studio' && <CompanionStudio />}
                </>
              }
            />
          </Routes>
        </SignedIn>

        {/* Clean Centered Landing View when Signed Out */}
        <SignedOut>
          <div className="flex flex-col items-center justify-center min-h-[70vh] py-12 px-4 text-center space-y-8 animate-fadeIn">
            <div className="relative">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-blue-500 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
                <Flame className="w-10 h-10 text-white animate-pulse" />
              </div>
              <div className="absolute -bottom-1 -right-1 p-1.5 rounded-full bg-emerald-500 text-white shadow-md">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
            </div>

            <div className="max-w-2xl space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Official JEE Main &amp; Advanced Syllabus Grounded</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-black text-slate-100 tracking-tight">
                JEE Progressive Doubt Resolution &amp; Companion Studio
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-xl mx-auto">
                Sign in to access 3-tier progressive hint doubt resolution, intelligent Qdrant RAG test papers, high-yield companion formula sheets, and Ebbinghaus forgetting curve analytics.
              </p>
            </div>

            {/* Feature Highlights Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl w-full text-left">
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md space-y-2">
                <div className="p-2 w-fit rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                  <BrainCircuit className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-200">3-Tier Progressive Scaffolding</h3>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Never gives away answers. Guides you through conceptual nudges, equation setups, and step verification.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md space-y-2">
                <div className="p-2 w-fit rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
                  <Layers className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-200">Companion Studio &amp; LaTeX</h3>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Synthesize master formula sheets, cheat sheets, and flashcards grounded in syllabus vectors.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md space-y-2">
                <div className="p-2 w-fit rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-200">Ebbinghaus Spaced Repetition</h3>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Automated decay tracking calculates memory strength and queues overdue topics before exams.
                </p>
              </div>
            </div>

            {/* Primary Action Button */}
            <div className="pt-2">
              <SignInButton mode="modal">
                <button
                  type="button"
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-2xl text-sm font-extrabold bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 hover:from-indigo-500 hover:via-purple-500 hover:to-blue-500 text-white shadow-xl shadow-indigo-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
                >
                  <span>Sign In to Access Companion Studio</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </SignInButton>
            </div>
          </div>
        </SignedOut>
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        JEE Doubt Resolution &amp; Test Series • 3-Tier Progressive Scaffolding &amp; Qdrant RAG (Google Gemini)
      </footer>
    </div>
  );
}
