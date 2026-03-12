import { useState, type KeyboardEvent } from 'react'
import { useVoiceClient } from '../hooks/useVoiceClient'
import './VoiceChat.css'

export function VoiceChat() {
  const [textInput, setTextInput] = useState('')
  
  const {
    isConnected,
    isRecording,
    isProcessing,
    transcript,
    response,
    error,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    sendText,
    clearHistory,
  } = useVoiceClient({
    onTranscript: (text) => console.log('Transcript:', text),
    onResponse: (text) => console.log('Response:', text),
    onError: (err) => console.error('Error:', err),
  })

  const handleConnect = () => {
    if (isConnected) {
      disconnect()
    } else {
      connect()
    }
  }

  const handleRecord = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const handleSendText = () => {
    if (textInput.trim()) {
      sendText(textInput.trim())
      setTextInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendText()
    }
  }

  return (
    <div className="voice-chat">
      <header className="voice-chat-header">
        <h1>🎤 VoiceClaw</h1>
        <p className="subtitle">Real-time Voice Assistant powered by OpenClaw</p>
      </header>

      <div className="connection-status">
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
        <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        <button 
          className={`btn ${isConnected ? 'btn-danger' : 'btn-primary'}`}
          onClick={handleConnect}
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      <div className="transcript-panel">
        <h2>📝 Your Speech</h2>
        <div className="transcript-text">
          {transcript || <span className="placeholder">Start speaking...</span>}
        </div>
      </div>

      <div className="response-panel">
        <h2>🤖 Response</h2>
        <div className="response-text">
          {response || <span className="placeholder">Waiting for response...</span>}
        </div>
      </div>

      <div className="controls">
        <button
          className={`btn btn-record ${isRecording ? 'recording' : ''}`}
          onClick={handleRecord}
          disabled={!isConnected}
        >
          {isRecording ? '⏹️ Stop Recording' : '🎤 Start Recording'}
        </button>

        {isProcessing && (
          <span className="processing-indicator">
            ⏳ Processing...
          </span>
        )}

        <button
          className="btn btn-secondary"
          onClick={clearHistory}
          disabled={!transcript && !response}
        >
          🗑️ Clear
        </button>
      </div>

      <div className="text-input-panel">
        <h3>Or type your message:</h3>
        <div className="text-input-row">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={!isConnected}
          />
          <button
            className="btn btn-primary"
            onClick={handleSendText}
            disabled={!isConnected || !textInput.trim()}
          >
            Send
          </button>
        </div>
      </div>

      <footer className="voice-chat-footer">
        <p>
          🦞 Powered by <a href="https://github.com/openclaw/openclaw" target="_blank" rel="noopener noreferrer">OpenClaw</a>
          {' '}&{' '}
          <a href="https://github.com/carlory/voiceclaw" target="_blank" rel="noopener noreferrer">VoiceClaw</a>
        </p>
      </footer>
    </div>
  )
}
