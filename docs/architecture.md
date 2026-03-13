# VoiceClaw 架构文档

## 概述

VoiceClaw 是一个实时语音对话系统，使用 WebSocket 实现低延迟的双向通信。

## 核心组件

### 1. Voice Server (FastAPI)

Python 后端服务，处理语音识别、合成和 LLM 对话。

#### 模块结构

```
voice-server/
├── src/
│   ├── config.py        # Pydantic Settings 配置
│   ├── main.py          # FastAPI 应用入口
│   │
│   ├── stt/             # 语音识别
│   │   ├── __init__.py
│   │   └── qwen_asr.py  # Qwen3-ASR + MLX
│   │
│   ├── tts/             # 语音合成
│   │   ├── __init__.py
│   │   └── qwen_tts.py  # Qwen3-TTS + MLX
│   │
│   ├── gateway/         # OpenClaw Gateway 客户端
│   │   ├── __init__.py
│   │   └── client.py    # HTTP/SSE 客户端
│   │
│   └── ws/              # WebSocket 处理
│       ├── __init__.py
│       └── handler.py   # VoiceSession, 消息处理
│
└── tests/               # pytest 测试
```

#### 核心类

##### `VoiceSession`

管理单个 WebSocket 会话的生命周期。

**职责：**
- 音频缓冲和 VAD
- 调用 ASR 转录
- 调用 Gateway 获取 LLM 响应
- 句子级 TTS 合成
- 发送 WebSocket 消息

**关键方法：**
- `start()` / `stop()` - 生命周期管理
- `handle_message()` - 消息路由
- `flush_audio()` - 触发转录
- `_stream_llm_response()` - 流式响应处理
- `_synthesize_and_send_sentence()` - 句子级 TTS

##### `GatewayClient`

OpenClaw Gateway 的 HTTP 客户端。

**职责：**
- 连接池管理
- 普通 HTTP 聊天
- SSE 流式聊天
- 健康检查

**关键方法：**
- `start()` / `stop()` - 连接池生命周期
- `chat()` - 非流式聊天
- `chat_stream()` - 流式聊天（async generator）

### 2. Web Client (React)

前端应用，提供用户界面和音频处理。

#### 技术栈

- React 18 + TypeScript
- Vite
- Web Audio API

#### 核心功能

- 麦克风录音
- WebSocket 通信
- 音频流播放
- 聊天 UI

### 3. OpenClaw Gateway

外部服务，提供 LLM 能力。

**接口：**
- `POST /v1/chat/completions` - OpenAI 兼容 API
- 支持 `stream: true` 参数

## 数据流

### 1. 语音输入流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Microphone │────>│ Audio Buffer│────>│    VAD      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │ silence
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ WebSocket   │<────│VoiceSession │<────│  Qwen3-ASR  │
│  transcript │     │             │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Gateway    │────> OpenClaw
                    │  Client     │      Gateway
                    └──────┬──────┘
                           │ SSE stream
                           ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ WebSocket   │<────│  Sentence   │<────│ Qwen3-TTS   │
│   audio     │     │  Splitter   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 2. 文本输入流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Text Input │────>│VoiceSession │────>│  Gateway    │
└─────────────┘     │             │     │  Client     │
                    └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    (同语音输入流程)
```

## 关键设计决策

### 1. 句子级 TTS

**问题：** 等待完整 LLM 响应再合成会增加延迟。

**解决方案：** 流式接收 LLM 响应，遇到句末标点立即触发 TTS。

**句末标点：** `。！？.?!`

```python
# handler.py
SENTENCE_END_PATTERN = re.compile(r"[。！？.!?]")

async def _stream_llm_response(self, user_text: str):
    buffer = ""
    async for chunk in self.gateway_client.chat_stream(...):
        buffer += chunk
        # Check for sentence boundaries
        while SENTENCE_END_PATTERN.search(buffer):
            # Extract and TTS immediately
            ...
```

### 2. 连接池复用

**问题：** 每次 LLM 请求创建新 HTTP 连接增加延迟。

**解决方案：** GatewayClient 维护长连接，会话级别复用。

```python
class GatewayClient:
    async def start(self):
        self._client = httpx.AsyncClient(...)  # Long-lived

    async def stop(self):
        await self._client.aclose()
```

### 3. WebSocket 消息类型

设计了一套消息协议支持流式响应：

| 类型 | 方向 | 用途 |
|------|------|------|
| `response_start` | S→C | 开始响应 |
| `response_chunk` | S→C | 文本块 |
| `audio` | S→C | TTS 音频（句子级） |
| `response_end` | S→C | 结束响应 |
| `done` | S→C | 交互完成 |

### 4. Fallback 机制

**问题：** Gateway 可能不可用。

**解决方案：**
1. 流式失败时使用 fallback 消息
2. 不影响 WebSocket 连接稳定性

```python
try:
    async for chunk in self.gateway_client.chat_stream(...):
        ...
except Exception as e:
    # Fallback
    await self._send_message(MessageType.RESPONSE_CHUNK, text="抱歉...")
```

## 性能优化

### 1. MLX 加速

使用 Apple MLX 框架进行 ASR/TTS 推理，充分利用 Apple Silicon。

### 2. 流式处理

- SSE 流式 LLM 响应
- 句子级 TTS
- WebSocket 实时推送

### 3. 连接池

复用 HTTP 连接，减少握手开销。

## 扩展性

### 添加新的 STT/TTS 引擎

1. 实现 `STTEngine` / `TTSEngine` 接口
2. 在 `config.py` 添加配置
3. 在 `src/stt/` 或 `src/tts/` 添加模块

### 添加新的 LLM 后端

1. 修改 `GatewayClient` 支持新 API
2. 或创建新的客户端类

## 测试策略

### 单元测试

- `tests/test_stt.py` - ASR 测试
- `tests/test_tts.py` - TTS 测试
- `tests/test_ws.py` - WebSocket 处理测试

### Mock 策略

- Mock ASR/TTS 引擎（不加载模型）
- Mock GatewayClient（不实际请求）
- Mock WebSocket

## 部署

### 开发环境

```bash
poetry run uvicorn src.main:app --reload
```

### 生产环境

```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8765
```

### Docker (TODO)

```dockerfile
FROM python:3.11-slim
# ...
```

## 监控

### 健康检查

```bash
curl http://localhost:8765/health
```

### 日志

- INFO: 会话开始/结束、转录结果
- DEBUG: 消息详情、音频块
- ERROR: 错误信息
