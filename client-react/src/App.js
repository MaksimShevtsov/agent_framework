import React, { useState, useEffect } from 'react';
import Chat from './Chat';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

function App() {
  const [user, setUser] = useState(null);
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '');
  const [wsToken, setWsToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load user from localStorage on app start
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
  }, []);

  // Create user and get WebSocket token
  const handleLogin = async (username) => {
    setLoading(true);
    setError('');

    try {
      // Create user
      const userResponse = await fetch(`${API_BASE_URL}/chat/users/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          username: username,
          display_name: username
        })
      });

      if (!userResponse.ok) {
        throw new Error(`Failed to create user: ${userResponse.status}`);
      }

      const userData = await userResponse.json();

      // Get WebSocket token
      const tokenResponse = await fetch(`${API_BASE_URL}/chat/websocket-token/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          user_id: userData.id
        })
      });

      if (!tokenResponse.ok) {
        throw new Error(`Failed to get WebSocket token: ${tokenResponse.status}`);
      }

      const tokenData = await tokenResponse.json();

      setUser(userData);
      setWsToken(tokenData.token);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('apiKey', apiKey);

    } catch (err) {
      console.error('Login error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setWsToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('apiKey');
  };

  if (!user) {
    return (
      <div className="app">
        <div className="login-container">
          <div className="login-card">
            <h1>Voice AI Platform</h1>
            <p>Enter your credentials to start chatting</p>

            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              const username = formData.get('username');
              if (username && apiKey) {
                handleLogin(username);
              } else {
                setError('Please enter both username and API key');
              }
            }}>
              <div className="form-group">
                <label htmlFor="apiKey">API Key:</label>
                <input
                  type="password"
                  id="apiKey"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="username">Username:</label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  placeholder="Enter your username"
                  required
                />
              </div>

              {error && <div className="error-message">{error}</div>}

              <button type="submit" disabled={loading} className="login-button">
                {loading ? 'Connecting...' : 'Connect'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="app-header">
        <h1>Voice AI Platform</h1>
        <div className="user-info">
          <span>Welcome, {user.display_name || user.username}</span>
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </div>
      <Chat user={user} wsToken={wsToken} apiKey={apiKey} />
    </div>
  );
}

export default App;
