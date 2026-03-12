/**
 * VoiceClaw WebSocket Client
 * Real-time voice communication with OpenClaw
 */

import { useState, useCallback, useRef, useEffect } from 'react'

// WebSocket message types (must match server)
type MessageType = 'audio' | 'text' | 'transcript' | 'response' | 'error' | 'done'

interface WSMessage {
  type: MessageType
  data?: string  // base64 for audio
  text?: string  // for text messages
  language?: string
  speaker?: string
}

interface UseVoiceClientOptions {
  serverUrl?: string
  onTranscript?: (text: string, language: string) => void
  onResponse?: (text: string) => void
  onError?: (error: string) => void
}

interface VoiceClientState {
  isConnected: boolean
  isRecording: boolean
  isProcessing: boolean
  transcript: string
  response: string
  error: string | null
}

export function useVoiceClient(options: UseVoiceClientOptions = {}) {
  const {
    serverUrl = '/ws/voice',
    onTranscript,
    onResponse,
    onError,
  } = options

  const [state, setState] = useState<VoiceClientState>({
    isConnected: false,
    isRecording: false,
    isProcessing: false,
    transcript: '',
    response: '',
    error: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null)

  // Build full WebSocket URL from relative path
  const getWsUrl = useCallback((path: string) => {
    if (path.startsWith('ws://') || path.startsWith('wss://')) {
      return path
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${path}`
  }, [])

  // Cleanup recording resources
  const cleanupRecording = useCallback(() => {
    if (processorRef.current) {
      try { processorRef.current.disconnect() } catch { /* ignore */ }
      processorRef.current = null
    }

    if (audioContextRef.current) {
      try { audioContextRef.current.close() } catch { /* ignore */ }
      audioContextRef.current = null
    }

    if (mediaStreamRef.current) {
      try { mediaStreamRef.current.getTracks().forEach(track => track.stop()) } catch { /* ignore */ }
      mediaStreamRef.current = null
    }
  }, [])

  // Connect to WebSocket server
  const connect = useCallback(() => {
    // Guard against multiple clicks while connecting
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    const wsUrl = getWsUrl(serverUrl)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[VoiceClaw] Connected to server')
      setState(prev => ({ ...prev, isConnected: true, error: null }))
    }

    ws.onclose = () => {
      console.log('[VoiceClaw] Disconnected from server')
      // Cleanup recording resources on disconnect
      cleanupRecording()
      setState(prev => ({
        ...prev,
        isConnected: false,
        isRecording: false,
        isProcessing: false,
      }))
    }

    ws.onerror = (event) => {
      console.error('[VoiceClaw] WebSocket error:', event)
      setState(prev => ({ ...prev, error: 'WebSocket connection error' }))
      onError?.('WebSocket connection error')
    }

    ws.onmessage = async (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        console.log('[VoiceClaw] Received:', message.type)

        switch (message.type) {
          case 'transcript':
            setState(prev => ({
              ...prev,
              transcript: prev.transcript + (message.text || ''),
              isProcessing: true,
            }))
            onTranscript?.(message.text || '', message.language || 'Chinese')
            break

          case 'response':
            setState(prev => ({ ...prev, response: prev.response + (message.text || '') }))
            onResponse?.(message.text || '')
            break

          case 'audio':
            if (message.data) {
              await playAudio(message.data)
            }
            break

          case 'done':
            setState(prev => ({ ...prev, isProcessing: false }))
            break

          case 'error':
            // Reset isProcessing on error to prevent stuck UI
            setState(prev => ({ 
              ...prev, 
              error: message.text || 'Unknown error',
              isProcessing: false,
            }))
            onError?.(message.text || 'Unknown error')
            break
        }
      } catch (err) {
        console.error('[VoiceClaw] Failed to parse message:', err)
      }
    }
  }, [serverUrl, getWsUrl, cleanupRecording, onTranscript, onResponse, onError])

  // Disconnect from WebSocket server
  const disconnect = useCallback(() => {
    cleanupRecording()
    setState(prev => ({ ...prev, isRecording: false }))
    wsRef.current?.close()
    wsRef.current = null
  }, [cleanupRecording])

  // Play audio from base64
  const playAudio = async (base64Audio: string) => {
    let url: string | null = null
    try {
      // Decode base64 to array buffer
      const binaryString = atob(base64Audio)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      // Create audio blob (assuming WAV format from server)
      const blob = new Blob([bytes], { type: 'audio/wav' })
      url = URL.createObjectURL(blob)

      // Play audio
      const audio = new Audio(url)
      audioPlayerRef.current = audio
      await audio.play()

      const cleanup = () => {
        if (url) {
          URL.revokeObjectURL(url)
        }
        audioPlayerRef.current = null
      }

      audio.onended = cleanup
      audio.onerror = () => {
        console.error('[VoiceClaw] Audio playback error')
        cleanup()
      }
    } catch (err) {
      console.error('[VoiceClaw] Failed to play audio:', err)
      if (url) {
        URL.revokeObjectURL(url)
      }
      audioPlayerRef.current = null
    }
  }

  // Efficient base64 encoding for audio chunks
  const arrayToBase64 = (uint8Array: Uint8Array): string => {
    // Use chunked conversion for better performance
    const chunks: string[] = []
    const chunkSize = 8192
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
      const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length))
      chunks.push(String.fromCharCode(...chunk))
    }
    return btoa(chunks.join(''))
  }

  // Send audio data to server
  const sendAudio = useCallback((audioData: Int16Array) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('[VoiceClaw] WebSocket not connected')
      return
    }

    // Convert Int16Array to base64 (efficient)
    const uint8Array = new Uint8Array(audioData.buffer)
    const base64 = arrayToBase64(uint8Array)

    const message: WSMessage = {
      type: 'audio',
      data: base64,
    }

    wsRef.current.send(JSON.stringify(message))
  }, [])

  // Send text to server
  const sendText = useCallback((text: string, language: string = 'Chinese') => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('[VoiceClaw] WebSocket not connected')
      return
    }

    const message: WSMessage = {
      type: 'text',
      text,
      language,
    }

    wsRef.current.send(JSON.stringify(message))
    setState(prev => ({ ...prev, isProcessing: true }))
  }, [])

  // Start recording audio
  const startRecording = useCallback(async () => {
    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      mediaStreamRef.current = stream

      // Create audio context and processor
      const audioContext = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      // Process audio chunks
      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0)
        
        // Convert Float32 to Int16 (16-bit PCM)
        const pcmData = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]))
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }

        // Send to server
        sendAudio(pcmData)
      }

      // Route through a muted GainNode to avoid sidetone/echo
      const silentGain = audioContext.createGain()
      silentGain.gain.value = 0
      
      source.connect(processor)
      processor.connect(silentGain)
      silentGain.connect(audioContext.destination)

      setState(prev => ({ ...prev, isRecording: true, error: null }))
      console.log('[VoiceClaw] Recording started')
    } catch (err) {
      console.error('[VoiceClaw] Failed to start recording:', err)
      setState(prev => ({ ...prev, error: 'Failed to access microphone' }))
      onError?.('Failed to access microphone')
    }
  }, [sendAudio, onError])

  // Stop recording audio
  const stopRecording = useCallback(() => {
    cleanupRecording()
    setState(prev => ({ ...prev, isRecording: false }))
    console.log('[VoiceClaw] Recording stopped')
  }, [cleanupRecording])

  // Clear transcript and response
  const clearHistory = useCallback(() => {
    setState(prev => ({
      ...prev,
      transcript: '',
      response: '',
      error: null,
    }))
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    ...state,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    sendText,
    clearHistory,
  }
}
