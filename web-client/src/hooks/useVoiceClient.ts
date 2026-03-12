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
    serverUrl = `ws://${window.location.hostname}:8765/ws/voice`,
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
  const audioQueueRef = useRef<Int16Array[]>([])
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null)

  // Connect to WebSocket server
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const ws = new WebSocket(serverUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[VoiceClaw] Connected to server')
      setState(prev => ({ ...prev, isConnected: true, error: null }))
    }

    ws.onclose = () => {
      console.log('[VoiceClaw] Disconnected from server')
      setState(prev => ({ ...prev, isConnected: false }))
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
            setState(prev => ({ ...prev, error: message.text || 'Unknown error' }))
            onError?.(message.text || 'Unknown error')
            break
        }
      } catch (err) {
        console.error('[VoiceClaw] Failed to parse message:', err)
      }
    }
  }, [serverUrl, onTranscript, onResponse, onError])

  // Disconnect from WebSocket server
  const disconnect = useCallback(() => {
    stopRecording()
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  // Play audio from base64
  const playAudio = async (base64Audio: string) => {
    try {
      // Decode base64 to array buffer
      const binaryString = atob(base64Audio)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      // Create audio blob (assuming WAV format from server)
      const blob = new Blob([bytes], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)

      // Play audio
      const audio = new Audio(url)
      audioPlayerRef.current = audio
      await audio.play()

      audio.onended = () => {
        URL.revokeObjectURL(url)
        audioPlayerRef.current = null
      }
    } catch (err) {
      console.error('[VoiceClaw] Failed to play audio:', err)
    }
  }

  // Send audio data to server
  const sendAudio = useCallback((audioData: Int16Array) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('[VoiceClaw] WebSocket not connected')
      return
    }

    // Convert Int16Array to base64
    const uint8Array = new Uint8Array(audioData.buffer)
    let binary = ''
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i])
    }
    const base64 = btoa(binary)

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

      source.connect(processor)
      processor.connect(audioContext.destination)

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
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    setState(prev => ({ ...prev, isRecording: false }))
    console.log('[VoiceClaw] Recording stopped')
  }, [])

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
