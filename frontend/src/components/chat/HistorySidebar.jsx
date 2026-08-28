import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  History,
  MessageSquare,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  BookOpen,
  Atom,
  FlaskConical,
  Calculator,
  RefreshCw,
  Search,
  Trash2,
  Filter,
  X,
} from 'lucide-react';

function getApiUrl(endpoint) {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${apiBaseUrl}/api/v1${cleanEndpoint}`;
}

const SUBJECT_ICONS = {
  Physics: Atom,
  Chemistry: FlaskConical,
  Mathematics: Calculator,
};

const SUBJECT_COLORS = {
  Physics: 'text-indigo-400 border-indigo-500/30 bg-indigo-950/40',
  Chemistry: 'text-emerald-400 border-emerald-500/30 bg-emerald-950/40',
  Mathematics: 'text-blue-400 border-blue-500/30 bg-blue-950/40',
};

export default function HistorySidebar({
  isOpen,
  onToggle,
  onSelectSession,
  activeSessionId,
  onNewSession,
}) {
  const [sessions, setSessions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('All');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const url = getApiUrl('/sessions');
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to fetch sessions: ${res.statusText}`);
      }
      const data = await res.json();
      setSessions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('⚠️ [HISTORY] Could not load sessions from backend:', err);
      setError('Unable to load history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleSessionClick = async (sessionId) => {
    if (sessionId === activeSessionId) return;

    try {
      const url = getApiUrl(`/sessions/${sessionId}/history`);
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to fetch session history: ${res.statusText}`);
      }
      const historyData = await res.json();
      if (onSelectSession) {
        onSelectSession(historyData);
      }
    } catch (err) {
      console.error('❌ [HISTORY] Error fetching session messages:', err);
    }
  };

  // Async deletion handler: stops event propagation, calls DELETE endpoint, and updates local state instantly
  const handleDelete = async (sessionId, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }

    try {
      const url = getApiUrl(`/sessions/${sessionId}`);
      const res = await fetch(url, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        if (activeSessionId === sessionId && onNewSession) {
          onNewSession();
        }
      } else {
        console.warn(`⚠️ [HISTORY] Delete request returned status: ${res.status}`);
      }
    } catch (err) {
      console.error('❌ [HISTORY] Error deleting session:', err);
    }
  };

  // Filter sessions state array based on searchTerm (case-insensitive) and subjectFilter
  const filteredSessions = useMemo(() => {
    return sessions.filter((sess) => {
      const titleStr = (sess.title || '').toLowerCase();
      const topicStr = (sess.topic || '').toLowerCase();
      const idStr = (sess.session_id || '').toLowerCase();
      const querySearch = searchTerm.trim().toLowerCase();

      const matchesSearch =
        !querySearch ||
        titleStr.includes(querySearch) ||
        topicStr.includes(querySearch) ||
        idStr.includes(querySearch);

      const matchesSubject =
        subjectFilter === 'All' ||
        (sess.subject && sess.subject.toLowerCase() === subjectFilter.toLowerCase());

      return matchesSearch && matchesSubject;
    });
  }, [sessions, searchTerm, subjectFilter]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onToggle}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-30 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 left-0 h-full z-40 flex flex-col bg-slate-900/95 border-r border-slate-800 transition-all duration-300 ease-in-out backdrop-blur-xl ${
          isOpen ? 'w-80 translate-x-0' : 'w-0 -translate-x-full lg:w-16 lg:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="p-3.5 border-b border-slate-800 flex items-center justify-between gap-2">
          {isOpen ? (
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="p-1.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <History className="w-4 h-4" />
              </div>
              <div className="overflow-hidden">
                <h4 className="text-xs font-bold text-slate-100 truncate">Doubt History</h4>
                <p className="text-[10px] text-slate-400">Past Socratic Sessions</p>
              </div>
            </div>
          ) : (
            <div className="mx-auto p-1.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <History className="w-4 h-4" />
            </div>
          )}

          <div className="flex items-center gap-1">
            {isOpen && (
              <button
                type="button"
                onClick={fetchSessions}
                disabled={isLoading}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
                title="Refresh history"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            )}
            <button
              type="button"
              onClick={onToggle}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
              title={isOpen ? 'Collapse history' : 'Expand history'}
            >
              {isOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Action Controls (New Session + Search + Filter) */}
        {isOpen ? (
          <div className="p-3 border-b border-slate-800/80 space-y-2.5">
            {/* New Doubt Session Button */}
            <button
              type="button"
              onClick={onNewSession}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all"
              title="Start new doubt session"
            >
              <Plus className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">New Doubt Session</span>
            </button>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search topics or titles..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl pl-8 pr-7 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2 top-2 p-0.5 text-slate-500 hover:text-slate-300"
                  title="Clear search"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Subject Filter Dropdown */}
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
              <select
                value={subjectFilter}
                onChange={(e) => setSubjectFilter(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 cursor-pointer"
              >
                <option value="All">All Subjects</option>
                <option value="Physics">Physics</option>
                <option value="Chemistry">Chemistry</option>
                <option value="Mathematics">Mathematics</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="p-3 border-b border-slate-800/80">
            <button
              type="button"
              onClick={onNewSession}
              className="w-full flex items-center justify-center p-2 rounded-xl bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white transition-all shadow-md"
              title="Start new doubt session"
            >
              <Plus className="w-4 h-4 flex-shrink-0" />
            </button>
          </div>
        )}

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {isLoading && sessions.length === 0 ? (
            <div className="py-8 text-center space-y-2">
              <div className="w-4 h-4 border-2 border-indigo-500/30 border-t-indigo-400 rounded-full animate-spin mx-auto" />
              {isOpen && <p className="text-[11px] text-slate-500">Loading sessions...</p>}
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="py-8 text-center px-4">
              {isOpen ? (
                <>
                  <MessageSquare className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-400 font-medium">
                    {sessions.length === 0 ? 'No past doubts' : 'No matching sessions'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {sessions.length === 0
                      ? 'Ask a question to start your first Socratic coaching session.'
                      : 'Try clearing your search term or subject filter.'}
                  </p>
                </>
              ) : (
                <MessageSquare className="w-4 h-4 text-slate-600 mx-auto" />
              )}
            </div>
          ) : (
            filteredSessions.map((sess) => {
              const isSelected = sess.session_id === activeSessionId;
              const SubjectIcon = SUBJECT_ICONS[sess.subject] || BookOpen;
              const badgeStyle = SUBJECT_COLORS[sess.subject] || 'text-slate-400 border-slate-700 bg-slate-800';

              if (!isOpen) {
                return (
                  <button
                    key={sess.session_id}
                    type="button"
                    onClick={() => handleSessionClick(sess.session_id)}
                    className={`w-full p-2.5 rounded-xl flex items-center justify-center border transition-all ${
                      isSelected
                        ? 'bg-indigo-950/60 border-indigo-500 text-indigo-300 ring-1 ring-indigo-500/40'
                        : 'bg-slate-950/40 hover:bg-slate-800/80 border-slate-800/80 text-slate-400 hover:text-slate-200'
                    }`}
                    title={`${sess.title} (${sess.subject})`}
                  >
                    <SubjectIcon className="w-4 h-4" />
                  </button>
                );
              }

              return (
                <div
                  key={sess.session_id}
                  onClick={() => handleSessionClick(sess.session_id)}
                  className={`group relative w-full text-left p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-1.5 ${
                    isSelected
                      ? 'bg-indigo-950/50 border-indigo-500/80 text-slate-100 shadow-md shadow-indigo-950/30 ring-1 ring-indigo-500/40'
                      : 'bg-slate-950/30 hover:bg-slate-800/60 border-slate-800/60 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`inline-flex items-center gap-1 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded-md border ${badgeStyle}`}
                    >
                      <SubjectIcon className="w-2.5 h-2.5" />
                      {sess.subject || 'Physics'}
                    </span>

                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-slate-500 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        {formatDate(sess.created_at)}
                      </span>

                      {/* Delete Session Button */}
                      <button
                        type="button"
                        onClick={(e) => handleDelete(sess.session_id, e)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-950/60 transition-all"
                        title="Delete session"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <h5 className="text-xs font-semibold text-slate-200 line-clamp-2 leading-snug">
                    {sess.title}
                  </h5>

                  {sess.topic && (
                    <p className="text-[10px] text-slate-400 truncate">
                      {sess.topic}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/40">
                    <span className="font-mono">#{sess.session_id.slice(0, 8)}</span>
                    <span className="text-indigo-400 font-medium">
                      {sess.current_hint_level >= 4
                        ? 'Master Solution'
                        : sess.current_hint_level > 0
                        ? `Tier ${sess.current_hint_level}`
                        : 'Active'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        {isOpen && (
          <div className="p-3 border-t border-slate-800/80 text-center">
            <span className="text-[10px] text-slate-500 flex items-center justify-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              Socratic Progressive Mentoring
            </span>
          </div>
        )}
      </aside>
    </>
  );
}
