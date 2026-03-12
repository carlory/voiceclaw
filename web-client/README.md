# VoiceClaw Web Client

Real-time voice assistant web client for OpenClaw.

## Features

- 🎤 Real-time voice recording and streaming
- 🔴 WebSocket connection to VoiceClaw server
- 📝 Text input fallback
- 🌊 Modern React + TypeScript + Vite

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Usage

1. Start the VoiceClaw server (port 8765)
2. Open http://localhost:5173
3. Click "Connect" to establish WebSocket connection
4. Click "Start Recording" to speak, or type a message

## Configuration

The client connects to `ws://localhost:8765/ws/voice` by default. Update `serverUrl` in `useVoiceClient` hook to change.

---

🦞 Part of [VoiceClaw](https://github.com/carlory/voiceclaw) | Powered by [OpenClaw](https://github.com/openclaw/openclaw)
