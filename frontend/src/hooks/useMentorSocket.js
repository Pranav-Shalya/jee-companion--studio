import { useState, useEffect, useRef, useCallback } from 'react';

const SPECULATIVE_STATUSES = [
  'Querying Qdrant Vector Syllabus Knowledge...',
  'Evaluating Student Step against JEE Consensus...',
  'Checking Pedagogical Checkpoint Guardrails...',
  'Formulating Progressive Hint Escalation...',
  'Formatting KaTeX Equation Layout...',
];

function getWebSocketUrl(sessionId) {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const wsBase = apiBaseUrl.replace(/^http/, 'ws');
  return `${wsBase}/ws/mentor/${sessionId}`;
}

export function useMentorSocket() {
  const [sessionId, setSessionId] = useState(() => {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return `jee-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
  });

  const [connectionStatus, setConnectionStatus] = useState('CONNECTING'); // 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED'
  const [messages, setMessages] = useState([]);
  const [currentHintLevel, setCurrentHintLevel] = useState(0); // 0 = idle, 1 = Tier 1, 2 = Tier 2, 3 = Tier 3, 4 = Master Solution
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState(SPECULATIVE_STATUSES[0]);
  const [activeTopic, setActiveTopic] = useState(null);
  const [activeSubject, setActiveSubject] = useState('Physics');

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const loadingIntervalRef = useRef(null);
  const isMountedRef = useRef(true);

  // Rotating speculative status interval
  useEffect(() => {
    if (isLoading) {
      let idx = 0;
      setStatusText(SPECULATIVE_STATUSES[0]);
      loadingIntervalRef.current = setInterval(() => {
        idx = (idx + 1) % SPECULATIVE_STATUSES.length;
        setStatusText(SPECULATIVE_STATUSES[idx]);
      }, 2000);
    } else {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
      }
    }
    return () => {
      if (loadingIntervalRef.current) clearInterval(loadingIntervalRef.current);
    };
  }, [isLoading]);

  // Connect WebSocket with controlled backoff
  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const wsUrl = getWebSocketUrl(sessionId);
    console.log(`🔗 [WS] Connecting to: ${wsUrl} (Session ID: ${sessionId})`);
    setConnectionStatus('CONNECTING');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        console.log(`✅ [WS Connected]: Session ID ${sessionId}`);
        setConnectionStatus('CONNECTED');
        reconnectAttemptsRef.current = 0;
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          console.log('📨 [WS Message Received]:', data);
          setIsLoading(false);

          if (data.type === 'connected') {
            setConnectionStatus('CONNECTED');
            return;
          }

          if (data.type === 'hint_update') {
            setCurrentHintLevel(data.hint_level);
            if (data.topic) setActiveTopic(data.topic);

            setMessages((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                type: `hint_${data.hint_level}`,
                hintLevel: data.hint_level,
                tierName: data.tier_name || `Tier ${data.hint_level}`,
                topic: data.topic,
                complexity: data.complexity,
                content: data.content,
                evaluationFeedback: data.evaluation_feedback || null,
                canRequestMore: data.can_request_more,
                timestamp: new Date(),
              },
            ]);
          } else if (data.type === 'master_solution') {
            setCurrentHintLevel(4);
            setMessages((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                type: 'master_solution',
                hintLevel: 4,
                tierName: data.tier_name || 'Master Solution (Verified Math Proof)',
                topic: data.topic,
                content: data.content,
                canRequestMore: false,
                timestamp: new Date(),
              },
            ]);
          } else if (data.type === 'info') {
            setMessages((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                type: 'info',
                content: data.message,
                timestamp: new Date(),
              },
            ]);
          } else if (data.type === 'error') {
            setMessages((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                type: 'error',
                content: data.message,
                timestamp: new Date(),
              },
            ]);
          }
        } catch (err) {
          console.error('❌ [WS Parse Error]:', err);
          setIsLoading(false);
        }
      };

      ws.onerror = (err) => {
        if (!isMountedRef.current) return;
        console.warn('⚠️ [WS Error / Disconnect]:', err);
        setConnectionStatus('DISCONNECTED');
        setIsLoading(false);
      };

      ws.onclose = (event) => {
        if (!isMountedRef.current) return;
        console.log(`🔌 [WS Disconnected]: Code ${event.code}.`);
        setConnectionStatus('DISCONNECTED');

        const delay = Math.min(10000, 2000 * Math.pow(1.5, reconnectAttemptsRef.current));
        reconnectAttemptsRef.current += 1;

        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connect();
          }
        }, delay);
      };
    } catch (e) {
      console.error('❌ [WS Init Exception]:', e);
      if (isMountedRef.current) {
        setConnectionStatus('DISCONNECTED');
      }
    }
  }, [sessionId]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();
    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Send Initial Doubt (supports image attachment)
  const sendDoubt = useCallback(
    (doubtText, subject = 'Physics', imageBase64 = null) => {
      if (!doubtText?.trim() && !imageBase64) return;

      setActiveSubject(subject);
      setIsLoading(true);

      setMessages((prev) => [
        ...prev,
        {
          id: `msg-user-${Date.now()}`,
          type: 'user_question',
          subject,
          content: doubtText || 'Attached doubt diagram/question for analysis:',
          image: imageBase64 || null,
          timestamp: new Date(),
        },
      ]);

      const payloadObj = {
        action: 'new_doubt',
        query: doubtText || '',
        subject,
      };

      if (imageBase64) {
        payloadObj.image = imageBase64;
      }

      const payload = JSON.stringify(payloadObj);

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(payload);
      } else {
        connect();
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(payload);
          }
        }, 600);
      }
    },
    [connect]
  );

  // Submit Student Attempt for Socratic Checkpoint Evaluation
  const submitAttempt = useCallback(
    (attemptText, currentTier = currentHintLevel) => {
      if (isLoading || currentHintLevel >= 4) return;
      setIsLoading(true);

      const isStuck =
        !attemptText?.trim() ||
        attemptText.toLowerCase().includes('stuck') ||
        attemptText.toLowerCase().includes('help');

      setMessages((prev) => [
        ...prev,
        {
          id: `msg-attempt-${Date.now()}`,
          type: 'user_question',
          subject: activeSubject,
          content: isStuck
            ? 'I am stuck on this step. Please provide the next hint.'
            : `My attempt / response:\n${attemptText}`,
          timestamp: new Date(),
        },
      ]);

      const payload = JSON.stringify({
        action: 'evaluate_attempt',
        attempt: attemptText || 'I am stuck',
        current_tier: currentTier,
        query: attemptText || 'I need more help',
      });

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(payload);
      } else {
        connect();
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(payload);
          }
        }, 600);
      }
    },
    [isLoading, currentHintLevel, activeSubject, connect]
  );

  // Request Next Progressive Hint Tier
  const requestNextHint = useCallback(() => {
    submitAttempt('I am stuck');
  }, [submitAttempt]);

  // Skip / Request Master Solution
  const requestMasterSolution = useCallback(() => {
    if (isLoading || currentHintLevel >= 4) return;
    setIsLoading(true);

    const payload = JSON.stringify({
      action: 'solution',
      query: 'solution',
    });

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(payload);
    }
  }, [isLoading, currentHintLevel]);

  // Load Past / Historical Session Messages directly into State
  const loadHistoricalSession = useCallback((historyData) => {
    if (!historyData) return;
    if (wsRef.current) {
      wsRef.current.close();
    }
    setSessionId(historyData.session_id);
    setMessages(historyData.messages || []);
    setCurrentHintLevel(
      historyData.current_hint_level ??
        (historyData.messages
          ? Math.max(0, ...historyData.messages.map((m) => m.hintLevel || 0))
          : 0)
    );
    setActiveTopic(historyData.topic || null);
    if (historyData.subject) {
      setActiveSubject(historyData.subject);
    }
    setIsLoading(false);
  }, []);

  // Reset Session
  const resetSession = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const newId =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `jee-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setSessionId(newId);
    setMessages([]);
    setCurrentHintLevel(0);
    setActiveTopic(null);
    setIsLoading(false);
  }, []);

  // Send Test Handoff to Active Mentor
  const sendTestHandoff = useCallback(
    (handoffState) => {
      if (!handoffState) return;

      const questionText = handoffState.question_text || handoffState.text || '';
      const subject = handoffState.subject || 'Physics';
      const studentOpt = handoffState.student_option ? ` (Selected Option: ${handoffState.student_option})` : '';

      setActiveSubject(subject);
      setIsLoading(true);

      setMessages((prev) => [
        ...prev,
        {
          id: `msg-user-handoff-${Date.now()}`,
          type: 'user_question',
          subject,
          content: `I reviewed this question on the practice test${studentOpt}:\n\n${questionText}`,
          timestamp: new Date(),
        },
      ]);

      const payload = JSON.stringify({
        action: 'test_handoff',
        payload: handoffState,
      });

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(payload);
      } else {
        connect();
        const checkInterval = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            clearInterval(checkInterval);
            wsRef.current.send(payload);
          }
        }, 100);
        setTimeout(() => clearInterval(checkInterval), 4000);
      }
    },
    [connect]
  );

  return {
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
  };
}
