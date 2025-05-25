import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import './Signaling.css';

const Signaling = forwardRef(({ onSignal, onCallStateChange, userId }, ref) => {
  const [isInCall, setIsInCall] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [callStatus, setCallStatus] = useState('idle'); // idle, calling, connected, ended
  const [remoteUserId, setRemoteUserId] = useState(null);

  const localStreamRef = useRef(null);
  const remoteStreamRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const localAudioRef = useRef(null);
  const remoteAudioRef = useRef(null);

  // WebRTC configuration
  const rtcConfiguration = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
    ]
  };

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    handleRemoteSignal
  }));

  // Initialize peer connection
  const createPeerConnection = () => {
    const pc = new RTCPeerConnection(rtcConfiguration);

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('Sending ICE candidate:', event.candidate);
        onSignal({
          type: 'ice-candidate',
          data: event.candidate,
          target_user: remoteUserId
        });
      }
    };

    pc.ontrack = (event) => {
      console.log('Received remote stream:', event.streams[0]);
      remoteStreamRef.current = event.streams[0];
      if (remoteAudioRef.current) {
        remoteAudioRef.current.srcObject = event.streams[0];
      }
    };

    pc.onconnectionstatechange = () => {
      console.log('Connection state:', pc.connectionState);
      if (pc.connectionState === 'connected') {
        setCallStatus('connected');
        setIsConnecting(false);
        setIsInCall(true);
        onCallStateChange(true);
      } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
        handleEndCall();
      }
    };

    pc.oniceconnectionstatechange = () => {
      console.log('ICE connection state:', pc.iceConnectionState);
      if (pc.iceConnectionState === 'failed') {
        // Attempt ICE restart
        pc.restartIce();
      }
    };

    return pc;
  };

  // Get user media
  const getUserMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false
      });

      localStreamRef.current = stream;
      if (localAudioRef.current) {
        localAudioRef.current.srcObject = stream;
      }

      return stream;
    } catch (error) {
      console.error('Error accessing microphone:', error);
      throw new Error('Failed to access microphone. Please check permissions.');
    }
  };

  // Start a call
  const startCall = async (targetUserId = null) => {
    try {
      setIsConnecting(true);
      setCallStatus('calling');
      setRemoteUserId(targetUserId);

      // Get user media
      const stream = await getUserMedia();

      // Create peer connection
      const pc = createPeerConnection();
      peerConnectionRef.current = pc;

      // Add local stream to peer connection
      stream.getTracks().forEach(track => {
        pc.addTrack(track, stream);
      });

      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      console.log('Sending offer:', offer);
      onSignal({
        type: 'offer',
        data: offer,
        target_user: targetUserId
      });

    } catch (error) {
      console.error('Error starting call:', error);
      setIsConnecting(false);
      setCallStatus('idle');
      alert(error.message);
    }
  };

  // Answer a call
  const answerCall = async (offer, fromUserId) => {
    try {
      setIsConnecting(true);
      setCallStatus('connecting');
      setRemoteUserId(fromUserId);

      // Get user media
      const stream = await getUserMedia();

      // Create peer connection
      const pc = createPeerConnection();
      peerConnectionRef.current = pc;

      // Add local stream to peer connection
      stream.getTracks().forEach(track => {
        pc.addTrack(track, stream);
      });

      // Set remote description
      await pc.setRemoteDescription(new RTCSessionDescription(offer));

      // Create answer
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      console.log('Sending answer:', answer);
      onSignal({
        type: 'answer',
        data: answer,
        target_user: fromUserId
      });

    } catch (error) {
      console.error('Error answering call:', error);
      setIsConnecting(false);
      setCallStatus('idle');
      alert('Failed to answer call: ' + error.message);
    }
  };

  // Handle remote signaling
  const handleRemoteSignal = async (signal) => {
    try {
      console.log('Handling remote signal:', signal);

      if (!peerConnectionRef.current && (signal.type === 'offer' || signal.type === 'answer')) {
        console.log('No peer connection available');
        return;
      }

      switch (signal.type) {
        case 'offer':
          if (window.confirm(`Incoming call from user ${signal.from_user}. Accept?`)) {
            await answerCall(signal.data, signal.from_user);
          } else {
            // Send rejection signal
            onSignal({
              type: 'call-rejected',
              target_user: signal.from_user
            });
          }
          break;

        case 'answer':
          if (peerConnectionRef.current) {
            await peerConnectionRef.current.setRemoteDescription(
              new RTCSessionDescription(signal.data)
            );
          }
          break;

        case 'ice-candidate':
          if (peerConnectionRef.current) {
            await peerConnectionRef.current.addIceCandidate(
              new RTCIceCandidate(signal.data)
            );
          }
          break;

        case 'call-ended':
          handleEndCall();
          break;

        case 'call-rejected':
          setIsConnecting(false);
          setCallStatus('idle');
          alert('Call was rejected');
          break;

        default:
          console.log('Unknown signal type:', signal.type);
      }
    } catch (error) {
      console.error('Error handling remote signal:', error);
    }
  };

  // End call
  const handleEndCall = () => {
    console.log('Ending call');

    // Stop local stream
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    // Stop remote stream
    if (remoteStreamRef.current) {
      remoteStreamRef.current.getTracks().forEach(track => track.stop());
      remoteStreamRef.current = null;
    }

    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    // Clear audio elements
    if (localAudioRef.current) {
      localAudioRef.current.srcObject = null;
    }
    if (remoteAudioRef.current) {
      remoteAudioRef.current.srcObject = null;
    }

    // Send end call signal
    if (isInCall && remoteUserId) {
      onSignal({
        type: 'call-ended',
        target_user: remoteUserId
      });
    }

    // Reset state
    setIsInCall(false);
    setIsConnecting(false);
    setCallStatus('idle');
    setRemoteUserId(null);
    setIsMuted(false);
    onCallStateChange(false);
  };

  // Toggle mute
  const toggleMute = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
      }
    }
  };

  return (
    <div className="signaling-container">
      <div className="call-controls">
        {!isInCall && !isConnecting && (
          <button
            onClick={() => startCall()}
            className="call-button start-call"
          >
            📞 Start Call
          </button>
        )}

        {isConnecting && (
          <div className="connecting-status">
            <span className="connecting-spinner"></span>
            <span>{callStatus === 'calling' ? 'Calling...' : 'Connecting...'}</span>
            <button onClick={handleEndCall} className="call-button end-call">
              End Call
            </button>
          </div>
        )}

        {isInCall && (
          <div className="in-call-controls">
            <div className="call-status">
              <span className="call-icon active">📞</span>
              <span>Call Active</span>
            </div>

            <div className="call-buttons">
              <button
                onClick={toggleMute}
                className={`call-button mute-button ${isMuted ? 'muted' : ''}`}
              >
                {isMuted ? '🔇' : '🎤'}
              </button>

              <button
                onClick={handleEndCall}
                className="call-button end-call"
              >
                📞 End Call
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="call-status-display">
        <div className={`status-text ${callStatus}`}>
          {callStatus === 'idle' && 'Ready to call'}
          {callStatus === 'calling' && 'Calling...'}
          {callStatus === 'connected' && `Connected${remoteUserId ? ` to user ${remoteUserId}` : ''}`}
          {callStatus === 'ended' && 'Call ended'}
        </div>
      </div>

      {/* Audio elements */}
      <audio
        ref={localAudioRef}
        autoPlay
        muted
        style={{ display: 'none' }}
      />
      <audio
        ref={remoteAudioRef}
        autoPlay
        style={{ display: 'none' }}
      />
    </div>
  );
});

export default Signaling;
