# 🦞 VoiceClaw

> Voice interface for OpenClaw using Qwen3-ASR/TTS with MLX on Apple Silicon

**中文语音优先** - 支持 22 种中文方言，包括北京话、上海话、四川话等。

## 特性

- ✅ **Qwen3-ASR** - 中文语音识别，支持 22 种方言
- ✅ **Qwen3-TTS** - 中文语音合成，支持声音克隆
- ✅ **MLX 加速** - Apple Silicon 原生优化
- ✅ **WebSocket** - 实时双向通信
- ✅ **OpenClaw 集成** - 完整保留 Tools 和记忆能力
- ✅ **流式响应** - 低延迟体验

## 架构

```
Client (React)
    ↓ WebSocket
Voice Server (FastAPI)
    ├── Qwen3-ASR
    ├── Qwen3-TTS
    └── Silero VAD
    ↓ HTTP API
OpenClaw Gateway
```

## 快速开始

### 前置要求

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- Poetry
- OpenClaw 运行中

### 安装

```bash
# Clone
git clone https://github.com/carlory/voiceclaw.git
cd voiceclaw/voice-server

# Install dependencies
poetry install

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
poetry run uvicorn src.main:app --reload
```

### 验证

```bash
curl http://localhost:8765/health
# {"ok": true}
```

## 开发

### 项目结构

```
voiceclaw/
├── voice-server/       # Python 后端
│   ├── src/
│   │   ├── stt/       # Qwen3-ASR
│   │   ├── tts/       # Qwen3-TTS
│   │   ├── llm/       # OpenClaw 客户端
│   │   └── ws/        # WebSocket
│   └── tests/
│
├── voice-client/       # Web 前端 (TODO)
└── docs/              # 文档
```

### 测试

```bash
cd voice-server
poetry run pytest
```

### 代码风格

```bash
poetry run ruff check src/
poetry run mypy src/
```

## API

### HTTP

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | 健康检查 |
| POST | /stt | 语音转文字 |
| POST | /tts | 文字转语音 |
| POST | /chat | 对话（非流式）|

### WebSocket

| Event | Direction | Description |
|-------|-----------|-------------|
| audio | Client → Server | 音频流 |
| transcript | Server → Client | STT 结果 |
| response | Server → Client | LLM 回复 |
| audio | Server → Client | TTS 音频 |

详细 API 文档见 [docs/api.md](docs/api.md)。

## 性能

| 指标 | 目标值 |
|------|--------|
| STT 延迟 | < 100ms |
| TTS 延迟 | < 200ms |
| 端到端延迟 | < 500ms |
| 内存占用 | < 4GB |

## License

MIT

## 相关项目

- [OpenClaw](https://github.com/openclaw/openclaw) - AI Agent 框架
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) - 语音识别
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - 语音合成
- [MLX](https://github.com/ml-explore/mlx) - Apple Silicon 推理框架
