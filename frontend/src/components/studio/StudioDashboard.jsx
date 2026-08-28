import React, { useState, useEffect } from 'react';
import {
  Compass,
  PlusCircle,
  FileCode,
  Sparkles,
  BookMarked,
  CheckCircle2,
} from 'lucide-react';
import TopicSelector from './TopicSelector';
import ArtifactCard from './ArtifactCard';
import { api } from '../../services/api';

export default function StudioDashboard() {
  const [selectedSubject, setSelectedSubject] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showGenModal, setShowGenModal] = useState(false);
  const [genSubject, setGenSubject] = useState('Physics');
  const [genTopicName, setGenTopicName] = useState('');
  const [genArtifactType, setGenArtifactType] = useState('formula_sheet');
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    loadTopics();
    loadArtifacts();
  }, []);

  const loadTopics = async () => {
    try {
      setIsLoading(true);
      const res = await api.fetchStudioTopics();
      setTopics(res.topics || []);
      if (res.topics?.length > 0 && !selectedTopic) {
        setSelectedTopic(res.topics[0]);
      }
    } catch (err) {
      console.error('Error loading topics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadArtifacts = async () => {
    try {
      const res = await api.fetchStudioArtifacts();
      setArtifacts(res || []);
    } catch (err) {
      console.error('Error loading artifacts:', err);
    }
  };

  const handleCreateArtifact = async (e) => {
    e.preventDefault();
    if (!genTopicName.trim()) return;
    try {
      setIsGenerating(true);
      const newArtifact = await api.generateStudioArtifact({
        subject: genSubject,
        topic: genTopicName,
        artifact_type: genArtifactType,
      });
      setArtifacts((prev) => [newArtifact, ...prev]);
      setShowGenModal(false);
      setGenTopicName('');
    } catch (err) {
      console.error('Error generating artifact:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const displayedArtifacts = selectedTopic
    ? artifacts.filter(
        (a) =>
          a.topic.toLowerCase().includes(selectedTopic.topic_name.toLowerCase()) ||
          a.subject === selectedTopic.subject
      )
    : artifacts;

  return (
    <div className="space-y-6">
      {/* Studio Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
            <Compass className="w-3.5 h-3.5" />
            <span>Companion Revision & Artifact Hub</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100">JEE Companion Studio</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Explore syllabus-mapped high-yield topic modules, download LaTeX formula sheets, and generate tailored revision notes.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowGenModal(true)}
          className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-500/25 transition-all"
        >
          <Sparkles className="w-4 h-4" />
          <span>Generate Study Artifact</span>
        </button>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Topic Navigator */}
        <div className="lg:col-span-5 space-y-4">
          <TopicSelector
            selectedSubject={selectedSubject}
            onSelectSubject={setSelectedSubject}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            topics={topics}
            activeTopicId={selectedTopic?.topic_id}
            onSelectTopic={setSelectedTopic}
          />

          {/* Subtopic Drilldown Card */}
          {selectedTopic && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
                <BookMarked className="w-4 h-4 text-indigo-400" />
                {selectedTopic.topic_name} — Syllabus Breakdown
              </h4>
              <ul className="space-y-2">
                {selectedTopic.subtopics.map((subtopic, sIdx) => (
                  <li key={sIdx} className="flex items-start gap-2 text-xs text-slate-300">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{subtopic}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right Column: Artifacts Feed */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200">
              {selectedTopic ? `Artifacts for ${selectedTopic.topic_name}` : 'All Study Artifacts'}
            </h3>
            <span className="text-xs text-slate-400">{displayedArtifacts.length} Documents</span>
          </div>

          {displayedArtifacts.length === 0 ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-10 text-center">
              <FileCode className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">No artifacts generated for this topic yet.</p>
              <button
                type="button"
                onClick={() => {
                  if (selectedTopic) {
                    setGenSubject(selectedTopic.subject);
                    setGenTopicName(selectedTopic.topic_name);
                  }
                  setShowGenModal(true);
                }}
                className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline"
              >
                Generate one now
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {displayedArtifacts.map((art) => (
                <ArtifactCard key={art.artifact_id} artifact={art} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Generation Modal */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Generate JEE Study Artifact
              </h3>
              <button
                type="button"
                onClick={() => setShowGenModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateArtifact} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Subject</label>
                <select
                  value={genSubject}
                  onChange={(e) => setGenSubject(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="Physics">Physics</option>
                  <option value="Chemistry">Chemistry</option>
                  <option value="Mathematics">Mathematics</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Topic Name</label>
                <input
                  type="text"
                  value={genTopicName}
                  onChange={(e) => setGenTopicName(e.target.value)}
                  placeholder="e.g. Electromagnetic Induction & Lenz's Law"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Artifact Format</label>
                <select
                  value={genArtifactType}
                  onChange={(e) => setGenArtifactType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="formula_sheet">Formula Sheet (KaTeX LaTeX)</option>
                  <option value="revision_note">Revision Summary & Traps</option>
                  <option value="mindmap">Mindmap & Strategy Guide</option>
                  <option value="pyq_breakdown">PYQ Blueprint Breakdown</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating || !genTopicName.trim()}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-all"
                >
                  {isGenerating ? 'Synthesizing...' : 'Generate Artifact'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
