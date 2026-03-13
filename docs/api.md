# VoiceClaw API 文档

## HTTP API

### 健康检查

```http
GET /health
```

**Response:**
```json
{
  "ok": true
}
```

### 语音转文字

```http
POST /stt
Content-Type: application/json

{
  "audio": "<base64_encoded_audio>",
  "language": "zh"
}
```

**Response:**
```json
{
  "text": "你好",
  "language": "Chinese",
  "confidence": 0.95
}
```

### 文字转语音

```http
POST /tts
Content-Type: application/json

{
  "text": "你好",
  "speaker": "default"
}
```

**Response:**
```json
{
  "audio": "<base64_encoded_audio>",
  "sample_rate": 16000,
  "duration_ms": 500
}
```

---

## WebSocket API

### 连接

```
ws://localhost:8765/ws/voice
```

### 消息格式

所有消息均为 JSON 格式。

### 客户端 → 服务器

#### 音频消息

发送音频数据用于语音识别。

```typescript
interface AudioMessage {
  type: "audio";
  data: string;  // base64 encoded 16-bit PCM, 16kHz, mono
}
```

**示例:**
```json
{
  "type": "audio",
  "data": "//uAxAAA..."
}
```

#### 文本消息

直接发送文本，绕过语音识别。

```typescript
interface TextMessage {
  type: "text";
  text: string;
  language?: string;  // default: "Chinese"
}
```

**示例:**
```json
{
  "type": "text",
  "text": "你好"
}
```

### 服务器 → 客户端

#### 转录结果

语音识别结果。

```typescript
interface TranscriptMessage {
  type: "transcript";
  text: string;
  language: string;
}
```

**示例:**
```json
{
  "type": "transcript",
  "text": "你好",
  "language": "Chinese"
}
```

#### 响应开始

标记 LLM 响应开始。

```typescript
interface ResponseStartMessage {
  type: "response_start";
}
```

#### 响应块

流式文本响应块。

```typescript
interface ResponseChunkMessage {
  type: "response_chunk";
  text: string;
}
```

**示例:**
```json
{
  "type": "response_chunk",
  "text": "你好"
}
```

#### 音频响应

TTS 生成的音频（句子级）。

```typescript
interface AudioResponseMessage {
  type: "audio";
  data: string;  // base64 encoded 16-bit PCM, 16kHz
}
```

**示例:**
```json
{
  "type": "audio",
  "data": "//uAxAAA..."
}
```

#### 响应结束

标记 LLM 响应结束，包含完整文本。

```typescript
interface ResponseEndMessage {
  type: "response_end";
  text: string;  // 完整响应文本
}
```

#### 完成

标记一个完整交互周期结束。

```typescript
interface DoneMessage {
  type: "done";
}
```

#### 错误

错误信息。

```typescript
interface ErrorMessage {
  type: "error";
  text: string;
}
```

**示例:**
```json
{
  "type": "error",
  "text": "Gateway 连接失败"
}
```

---

## 交互流程

### 语音输入流程

```
Client                          Server
  │                               │
  │──── audio chunk ────────────>│
  │     (multiple)                │
  │                               │
  │                               │ [VAD detects silence]
  │                               │ [STT transcription]
  │                               │
  │<─── transcript ───────────────│
  │                               │
  │                               │ [Gateway LLM stream]
  │<─── response_start ───────────│
  │                               │
  │<─── response_chunk ───────────│ (multiple)
  │<─── audio ────────────────────│ (per sentence)
  │                               │
  │<─── response_end ─────────────│
  │<─── done ─────────────────────│
  │                               │
```

### 文本输入流程

```
Client                          Server
  │                               │
  │──── text ────────────────────>│
  │                               │
  │                               │ [Gateway LLM stream]
  │<─── transcript ───────────────│
  │<─── response_start ───────────│
  │                               │
  │<─── response_chunk ───────────│ (multiple)
  │<─── audio ────────────────────│ (per sentence)
  │                               │
  │<─── response_end ─────────────│
  │<─── done ─────────────────────│
  │                               │
```

---

## 错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| `Empty audio data` | 音频数据为空 | 检查音频输入 |
| `Empty text` | 文本为空 | 检查文本输入 |
| `Invalid JSON` | JSON 格式错误 | 检查消息格式 |
| `Unknown message type` | 未知消息类型 | 使用正确的 type |
| `Gateway 连接失败` | OpenClaw Gateway 不可用 | 检查 Gateway 状态 |
| `Transcription error` | ASR 失败 | 检查音频格式 |

---

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `127.0.0.1` | 服务器地址 |
| `PORT` | `8765` | 服务器端口 |
| `OPENCLAW_GATEWAY_URL` | `http://127.0.0.1:18789` | Gateway 地址 |
| `OPENCLAW_GATEWAY_TOKEN` | - | Gateway 认证 token |
| `OPENCLAW_MODEL` | `openclaw` | 模型名称 |
| `ASR_MODEL` | `Qwen/Qwen3-ASR-1.7B` | ASR 模型 |
| `TTS_MODEL` | `Qwen/Qwen3-TTS-1.7B` | TTS 模型 |
| `SAMPLE_RATE` | `16000` | 音频采样率 |
| `VAD_THRESHOLD` | `0.5` | VAD 能量阈值 |
| `VAD_MIN_SILENCE_MS` | `500` | 静音检测时长 |

---

## 客户端实现示例

### JavaScript/TypeScript

```typescript
const ws = new WebSocket('ws://localhost:8765/ws/voice');

// Handle messages
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    case 'transcript':
      console.log('User:', msg.text);
      break;
    case 'response_chunk':
      console.log('AI chunk:', msg.text);
      break;
    case 'audio':
      playAudio(msg.data);  // base64 to AudioContext
      break;
    case 'done':
      console.log('Turn complete');
      break;
    case 'error':
      console.error('Error:', msg.text);
      break;
  }
};

// Send text
ws.send(JSON.stringify({
  type: 'text',
  text: '你好'
}));

// Send audio
async function sendAudio(audioBuffer: ArrayBuffer) {
  const base64 = btoa(String.fromCharCode(...new Uint8Array(audioBuffer)));
  ws.send(JSON.stringify({
    type: 'audio',
    data: base64
  }));
}
```

### Python

```python
import asyncio
import websockets
import json
import base64

async def voice_client():
    async with websockets.connect('ws://localhost:8765/ws/voice') as ws:
        # Send text
        await ws.send(json.dumps({
            'type': 'text',
            'text': '你好'
        }))

        # Receive messages
        async for message in ws:
            msg = json.loads(message)

            if msg['type'] == 'transcript':
                print(f"User: {msg['text']}")
            elif msg['type'] == 'response_chunk':
                print(f"AI: {msg['text']}", end='', flush=True)
            elif msg['type'] == 'audio':
                audio = base64.b64decode(msg['data'])
                # Play audio...
            elif msg['type'] == 'done':
                print("\nTurn complete")
                break
            elif msg['type'] == 'error':
                print(f"Error: {msg['text']}")

asyncio.run(voice_client())
```
