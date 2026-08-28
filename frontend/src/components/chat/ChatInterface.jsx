import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ActiveMentorChat from './ActiveMentorChat';

/**
 * ChatInterface Component
 * Implements the Socratic progressive hint chat interface with WebSocket streaming
 * and Test Series state handoff resolution support.
 */
export default function ChatInterface(props) {
  return <ActiveMentorChat {...props} />;
}

export { ActiveMentorChat };
