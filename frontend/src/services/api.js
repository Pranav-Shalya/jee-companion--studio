/**
 * API & WebSocket Client for JEE Doubt Resolution & Companion Studio
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
const API_BASE = `${API_BASE_URL}/api/v1`;

export const api = {
  // --- Doubt Intake & Sessions ---
  async submitDoubt({ subject, query_text, image_base64, topic_hint }) {
    const response = await fetch(`${API_BASE}/doubts/intake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject,
        query_text,
        image_base64,
        topic_hint,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to submit doubt' }));
      throw new Error(error.detail || 'Failed to submit doubt');
    }
    return response.json();
  },

  async getDoubtSession(sessionId) {
    const response = await fetch(`${API_BASE}/doubts/${sessionId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch session: ${sessionId}`);
    }
    return response.json();
  },

  // --- 3-Tier Progressive Hint Progression ---
  async requestNextHint(sessionId, targetTier, studentNotes = null) {
    const response = await fetch(`${API_BASE}/hints/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        target_tier: targetTier,
        student_notes: studentNotes,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to unlock hint tier' }));
      throw new Error(error.detail || 'Failed to unlock hint tier');
    }
    return response.json();
  },

  async submitStudentAttempt(sessionId, attemptText) {
    const response = await fetch(`${API_BASE}/hints/attempt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        student_attempt_text: attemptText,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to evaluate attempt' }));
      throw new Error(error.detail || 'Failed to evaluate attempt');
    }
    return response.json();
  },

  // --- Companion Studio Resources ---
  async fetchStudioTopics(subject = null) {
    const url = subject ? `${API_BASE}/studio/topics?subject=${encodeURIComponent(subject)}` : `${API_BASE}/studio/topics`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch studio topics');
    return response.json();
  },

  async fetchStudioArtifacts(subject = null) {
    const url = subject ? `${API_BASE}/studio/artifacts?subject=${encodeURIComponent(subject)}` : `${API_BASE}/studio/artifacts`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch studio artifacts');
    return response.json();
  },

  async generateStudioArtifact({ subject, topic, artifact_type, custom_focus }) {
    const response = await fetch(`${API_BASE}/studio/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject,
        topic,
        artifact_type,
        custom_focus,
      }),
    });
    if (!response.ok) throw new Error('Failed to generate studio artifact');
    return response.json();
  },

  getArtifactDownloadUrl(artifactId) {
    return `${API_BASE}/studio/download/${artifactId}`;
  },
};

/**
 * WebSocket helper for real-time Socratic coaching
 */
export function createDoubtWebSocket(sessionId, handlers = {}) {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const wsBase = apiBaseUrl.replace(/^http/, 'ws');
  const wsUrl = `${wsBase}/ws/session/${sessionId}`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    if (handlers.onOpen) handlers.onOpen();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (handlers.onMessage) handlers.onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    if (handlers.onError) handlers.onError(error);
  };

  ws.onclose = () => {
    if (handlers.onClose) handlers.onClose();
  };

  return {
    sendHintRequest: (targetTier) => {
      ws.send(JSON.stringify({ type: 'request_hint', target_tier: targetTier }));
    },
    sendStudentStep: (stepText) => {
      ws.send(JSON.stringify({ type: 'submit_step', step_text: stepText }));
    },
    close: () => ws.close(),
  };
}
