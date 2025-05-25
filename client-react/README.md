# Voice AI Platform - React Frontend

This is the React frontend for the Voice AI Platform, featuring real-time chat with WebSocket communication and WebRTC voice calling capabilities.

## Features

- **Real-time Chat**: Text messaging with live updates via WebSocket
- **Voice Calling**: WebRTC-based peer-to-peer voice communication
- **Modern UI**: Beautiful, responsive design with glassmorphism effects
- **Typing Indicators**: See when other users are typing
- **Connection Status**: Visual feedback for WebSocket connection state
- **API Integration**: REST API for message persistence and user management

## Technologies Used

- React 18.2.0
- WebSocket for real-time communication
- WebRTC for voice calling
- Responsive CSS with modern styling
- REST API integration

## Setup

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
Copy `.env` and configure:
```
REACT_APP_API_BASE_URL=http://localhost:8000/api
REACT_APP_WS_BASE_URL=ws://localhost:8000/ws
REACT_APP_APP_NAME=Voice AI Platform
```

3. Start the development server:
```bash
npm start
```

The app will be available at `http://localhost:3000`

## Usage

### Getting Started

1. **Login**: Enter your API key and username to connect
2. **Chat**: Send text messages in real-time
3. **Voice Call**: Click "Start Call" to initiate a voice call
4. **Controls**: Use mute/unmute and end call buttons during calls

### API Key

You need a valid API key from the backend server. You can generate one using the Django admin interface or API endpoints.

### WebSocket Connection

The app automatically connects to the WebSocket server using the provided token. Connection status is displayed in the sidebar.

### Voice Calling

Voice calls use WebRTC for peer-to-peer communication. Make sure to:
- Allow microphone access when prompted
- Have a stable internet connection
- Use a modern browser with WebRTC support

## Components

### App.js
Main application component handling authentication and user management.

### Chat.js
Core chat interface with message display, WebSocket communication, and integration with voice calling.

### Signaling.js
WebRTC signaling component managing voice call setup, peer connections, and call controls.

## Styling

The application uses modern CSS with:
- Glassmorphism effects
- Gradient backgrounds
- Smooth animations
- Responsive design
- Mobile-first approach

## API Endpoints Used

- `POST /api/chat/users/` - Create chat user
- `POST /api/chat/websocket-token/` - Get WebSocket token
- `POST /api/chat/messages/` - Send messages via REST

## WebSocket Events

### Outgoing
- `chat_message` - Send text message
- `webrtc_signal` - WebRTC signaling
- `typing` - Typing indicators
- `ping` - Keep connection alive

### Incoming
- `connection_established` - Connection confirmation
- `chat_message` - Receive text message
- `webrtc_signal` - WebRTC signaling
- `typing_indicator` - Typing status
- `voice_data` - Voice data processing
- `error` - Error messages
- `pong` - Ping response

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

WebRTC features require modern browser support for optimal experience.

## Development

### Running Tests
```bash
npm test
```

### Building for Production
```bash
npm run build
```

### Linting
```bash
npm run lint
```

## Troubleshooting

### Connection Issues
- Check API key validity
- Verify backend server is running
- Check WebSocket URL configuration

### Voice Call Issues
- Allow microphone permissions
- Check internet connection stability
- Ensure WebRTC is supported in browser
- Check for firewall/network restrictions

### Performance
- Use Chrome DevTools for debugging
- Monitor WebSocket connection status
- Check console for error messages
