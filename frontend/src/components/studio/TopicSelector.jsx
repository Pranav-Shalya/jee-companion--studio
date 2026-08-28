import React from 'react';
import { BookOpen, Search, Layers, Atom, FlaskConical, Binary } from 'lucide-react';

const SUBJECT_FILTERS = [
  { id: 'ALL', label: 'All Subjects', icon: Layers },
  { id: 'Physics', label: 'Physics', icon: Atom, color: 'text-indigo-400' },
  { id: 'Chemistry', label: 'Chemistry', icon: FlaskConical, color: 'text-emerald-400' },
  { id: 'Mathematics', label: 'Mathematics', icon: Binary, color: 'text-amber-400' },
];

export default function TopicSelector({
  selectedSubject,
  onSelectSubject,
  searchQuery,
  onSearchChange,
  topics = [],
  activeTopicId,
  onSelectTopic,
}) {
  const filteredTopics = topics.filter((topic) => {
    const matchesSubject =
      selectedSubject === 'ALL' || topic.subject === selectedSubject;
    const matchesSearch =
      topic.topic_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      topic.subtopics.some((st) => st.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSubject && matchesSearch;
  });

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4.5 backdrop-blur-md space-y-4">
      {/* Subject Filter Tabs */}
      <div className="flex flex-wrap gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
        {SUBJECT_FILTERS.map((tab) => {
          const Icon = tab.icon;
          const isActive = selectedSubject === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectSubject(tab.id)}
              className={`flex-1 min-w-[100px] flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${tab.color || 'text-slate-300'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter JEE topics, subtopics, or theorems..."
          className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl pl-9.5 pr-4 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none"
        />
      </div>

      {/* Topic List */}
      <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
        {filteredTopics.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-6">No topics matched your search filter.</p>
        ) : (
          filteredTopics.map((t) => {
            const isSelected = activeTopicId === t.topic_id;
            return (
              <div
                key={t.topic_id}
                onClick={() => onSelectTopic(t)}
                className={`cursor-pointer border rounded-xl p-3 transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-950/40 shadow-sm ring-1 ring-indigo-500/40'
                    : 'border-slate-800/80 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-bold text-slate-200">{t.topic_name}</span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                      t.jee_weightage === 'High'
                        ? 'bg-rose-950/40 border-rose-800 text-rose-300'
                        : 'bg-blue-950/40 border-blue-800 text-blue-300'
                    }`}
                  >
                    {t.jee_weightage} Weightage
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                  <span>{t.subject}</span>
                  <span>•</span>
                  <span>{t.subtopics.length} Subtopics</span>
                  <span>•</span>
                  <span>{t.recommended_pyqs_count} PYQs</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
