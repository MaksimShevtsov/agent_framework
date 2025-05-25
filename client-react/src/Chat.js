import React, { useState, useEffect, useRef, useCallback } from 'react';
import Signaling from './Signaling';
import './Chat.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000/ws';

function Chat({ user, wsToken, apiKey }) {
  const [ws, setWs] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [conversationId] = useState(() => 'conv_' + Date.now());
  const [isTyping, setIsTyping] = useState(false);
  const [typingUsers, setTypingUsers] = useState([]);
  const [voiceCallActive, setVoiceCallActive] = useState(false);

  const messagesEndRef = useRef(null);
  const signalingRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Handle typing indicators
  const handleTypingIndicator = useCallback((data) => {
    if (data.is_typing) {
      setTypingUsers(prev => {
        if (!prev.includes(data.user_id)) {
          return [...prev, data.user_id];
        }
        return prev;
      });
    } else {
      setTypingUsers(prev => prev.filter(id => id !== data.user_id));
    }
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data) => {
    console.log('Received WebSocket message:', data);

    switch (data.type) {
      case 'connection_established':
        console.log('Connection established with session:', data.session_id);
        break;

      case 'chat_message':
        setMessages(prev => [...prev, {
          ...data.message,
          timestamp: new Date(data.message.timestamp)
        }]);
        break;

      case 'typing_indicator':
        handleTypingIndicator(data);
        break;

      case 'webrtc_signal':
        if (signalingRef.current) {
          signalingRef.current.handleRemoteSignal(data.signal);
        }
        break;

      case 'voice_data':
        console.log('Received voice data:', data);
        break;

      case 'error':
        console.error('Server error:', data.message);
        break;

      case 'pong':
        console.log('Pong received');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }, [handleTypingIndicator]);



  // WebSocket connection
  useEffect(() => {
    if (!wsToken) return;

    const wsUrl = `${WS_BASE_URL}/chat/${conversationId}/${wsToken}/`;
    console.log('Connecting to:', wsUrl);

    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setConnectionStatus('connected');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    websocket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setConnectionStatus('disconnected');

      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (wsToken) {
          setConnectionStatus('reconnecting');
        }
      }, 3000);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('error');
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [wsToken, conversationId, handleWebSocketMessage]);

  // Send message via REST API
  const sendMessage = async (content) => {
    if (!content.trim()) return;

    try {
      const response = await fetch(`${API_BASE_URL}/chat/messages/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          content: content,
          sender: 'user'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.status}`);
      }

      // Also send via WebSocket for real-time updates
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'chat_message',
          message: content
        }));
      }

    } catch (err) {
      console.error('Failed to send message:', err);
      // Add error message to chat
      setMessages(prev => [...prev, {
        id: Date.now(),
        content: `Error: ${err.message}`,
        sender: 'system',
        timestamp: new Date()
      }]);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (newMessage.trim()) {
      sendMessage(newMessage);
      setNewMessage('');
      sendTypingIndicator(false);
    }
  };

  // Send typing indicator
  const sendTypingIndicator = (typing) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'typing',
        is_typing: typing
      }));
    }
  };

  // Handle typing
  const handleTyping = (e) => {
    setNewMessage(e.target.value);

    if (!isTyping) {
      setIsTyping(true);
      sendTypingIndicator(true);
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      sendTypingIndicator(false);
    }, 1000);
  };

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle WebRTC signaling
  const handleSignal = (signal) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'webrtc_signal',
        signal_type: signal.type,
        data: signal.data,
        target_user: signal.target_user
      }));
    }
  };

  // Send ping to keep connection alive
  useEffect(() => {
    if (ws && connectionStatus === 'connected') {
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Ping every 30 seconds

      return () => clearInterval(pingInterval);
    }
  }, [ws, connectionStatus]);

  return (
    <div className="chat-container">
      <div className="chat-sidebar">
        <div className="connection-status">
          <div className={`status-indicator ${connectionStatus}`}>
            <span className="status-dot"></span>
            {connectionStatus === 'connected' && 'Connected'}
            {connectionStatus === 'disconnected' && 'Disconnected'}
            {connectionStatus === 'reconnecting' && 'Reconnecting...'}
            {connectionStatus === 'error' && 'Connection Error'}
          </div>
        </div>

        <div className="voice-controls">
          <h3>Voice Chat</h3>
          <Signaling
            ref={signalingRef}
            onSignal={handleSignal}
            onCallStateChange={setVoiceCallActive}
            userId={user.id}
          />
        </div>

        <div className="conversation-info">
          <h3>Conversation</h3>
          <p><strong>ID:</strong> {conversationId}</p>
          <p><strong>User:</strong> {user.username}</p>
          {voiceCallActive && (
            <div className="call-indicator">
              <span className="call-icon">📞</span>
              <span>Voice call active</span>
            </div>
          )}
        </div>
      </div>

      <div className="chat-main">
        <div className="messages-container">
          <div className="messages">
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.sender}`}>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-time">
                    {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}
                  </div>
                </div>
              </div>
            ))}

            {typingUsers.length > 0 && (
              <div className="typing-indicator">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span>Someone is typing...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="message-form">
          <div className="input-container">
            <input
              type="text"
              value={newMessage}
              onChange={handleTyping}
              placeholder="Type your message..."
              disabled={connectionStatus !== 'connected'}
              className="message-input"
            />
            <button
              type="submit"
              disabled={!newMessage.trim() || connectionStatus !== 'connected'}
              className="send-button"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Chat;
