import React, { useState } from 'react';
import { Image as ImageIcon, Send, X, Sparkles, BookOpen, AlertCircle } from 'lucide-react';

const SUBJECTS = [
  { id: 'Physics', label: 'Physics', color: 'border-indigo-500 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20' },
  { id: 'Chemistry', label: 'Chemistry', color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' },
  { id: 'Mathematics', label: 'Mathematics', color: 'border-amber-500 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20' },
];

const SAMPLE_DOUBTS = {
  Physics: "A particle of mass m moves along a circle of radius R with uniform speed v. Find the magnitude of average acceleration during the time interval in which it travels half a revolution.",
  Chemistry: "For the reaction N2(g) + 3H2(g) <=> 2NH3(g), ΔH is negative. Explain how increasing pressure and temperature shifts equilibrium using Le Chatelier's principle and van 't Hoff equation.",
  Mathematics: "Evaluate the definite integral: I = \\int_0^{\\pi/2} \\frac{\\sqrt{\\sin x}}{\\sqrt{\\sin x} + \\sqrt{\\cos x}} dx using King's property.",
};

export default function DoubtInput({ onSubmit, isLoading }) {
  const [subject, setSubject] = useState('Physics');
  const [queryText, setQueryText] = useState('');
  const [topicHint, setTopicHint] = useState('');
  const [imageBase64, setImageBase64] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result;
        setImageBase64(base64String);
        setImagePreview(base64String);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImageBase64(null);
    setImagePreview(null);
  };

  const loadSample = () => {
    setQueryText(SAMPLE_DOUBTS[subject]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!queryText.trim() && !imageBase64) return;
    onSubmit({
      subject,
      query_text: queryText,
      image_base64: imageBase64,
      topic_hint: topicHint || undefined,
    });
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl transition-all">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        {/* Subject Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Subject:</span>
          <div className="flex gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
            {SUBJECTS.map((sub) => (
              <button
                key={sub.id}
                type="button"
                onClick={() => setSubject(sub.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  subject === sub.id
                    ? `${sub.color} border shadow-sm font-semibold`
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {sub.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sample Doubt Button */}
        <button
          type="button"
          onClick={loadSample}
          className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 hover:bg-indigo-950/70 border border-indigo-800/50 px-3 py-1.5 rounded-lg transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Load {subject} Sample
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Main Problem Input */}
        <div className="relative">
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder={`Type your ${subject} problem statement here or paste LaTeX equations (e.g., $F = ma$ or $$\\int f(x)dx$$)...`}
            rows={4}
            className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-4 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 resize-y transition-all"
          />
        </div>

        {/* Image Preview Banner */}
        {imagePreview && (
          <div className="relative inline-block border border-slate-700 bg-slate-950 rounded-lg p-1.5 overflow-hidden">
            <img src={imagePreview} alt="Problem Upload" className="h-24 w-auto rounded object-cover" />
            <button
              type="button"
              onClick={removeImage}
              className="absolute top-2 right-2 bg-rose-600 hover:bg-rose-700 text-white rounded-full p-1 shadow-lg transition-all"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Bottom Actions Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-3">
            {/* Image Upload Trigger */}
            <label className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700 px-3 py-2 rounded-lg transition-all">
              <ImageIcon className="w-4 h-4 text-indigo-400" />
              <span>Attach Problem / Diagram</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>

            {/* Optional Topic Tag */}
            <input
              type="text"
              value={topicHint}
              onChange={(e) => setTopicHint(e.target.value)}
              placeholder="Topic tag (optional)"
              className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-1.5 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none"
            />
          </div>

          {/* Submit Doubt */}
          <button
            type="submit"
            disabled={isLoading || (!queryText.trim() && !imageBase64)}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
          >
            {isLoading ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing Problem...
              </span>
            ) : (
              <>
                <span>Get Progressive Hints</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Syllabus Boundary Note */}
      <div className="mt-3.5 flex items-center gap-2 text-[11px] text-slate-400 border-t border-slate-800/60 pt-2.5">
        <AlertCircle className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
        <span>
          <strong>Pedagogical Standard:</strong> Direct answers are withheld to build problem-solving intuition. Solutions progress across 3 tiers (Concept → Strategy → Walkthrough).
        </span>
      </div>
    </div>
  );
}
