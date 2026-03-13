# 🦞 VoiceClaw

> Voice interface for OpenClaw using Qwen3-ASR/TTS with MLX on Apple Silicon

**中文语音优先** - 支持 22 种中文方言，包括北京话、上海话、四川话等。

## 特性

- ✅ **Qwen3-ASR** - 中文语音识别，支持 22 种方言
- ✅ **Qwen3-TTS** - 中文语音合成，支持声音克隆
- ✅ **MLX 加速** - Apple Silicon 原生优化
- ✅ **WebSocket** - 实时双向通信
- ✅ **OpenClaw Gateway 集成** - 完整保留 Tools 和记忆能力
- ✅ **SSE 流式响应** - 句子级 TTS，低延迟体验
- ✅ **React Web 客户端** - 现代化 UI

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Web Client (React)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Mic Input  │  │ Audio Player │  │  Chat UI      │  │
│  └──────┬──────┘  └──────▲───────┘  └───────▲───────┘  │
└─────────┼────────────────┼──────────────────┼──────────┘
          │ WebSocket      │ Audio           │ Text
          ▼                │                 │
┌─────────────────────────────────────────────────────────┐
│                Voice Server (FastAPI)                    │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │  WebSocket   │──│ VoiceSession  │──│  Gateway    │  │
│  │   Handler    │  │  ┌────────┐   │  │  Client     │  │
│  └──────────────┘  │  │ASR/TTS │   │  └──────┬──────┘  │
│                    │  └────────┘   │         │         │
│                    └───────────────┘         │         │
└──────────────────────────────────────────────┼─────────┘
                                               │ HTTP/SSE
                                               ▼
┌─────────────────────────────────────────────────────────┐
│                OpenClaw Gateway                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  LLM API    │  │  Tools       │  │  Memory       │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 前置要求

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- Node.js 18+
- Poetry
- OpenClaw Gateway 运行中

### 安装

```bash
# Clone
git clone https://github.com/carlory/voiceclaw.git
cd voiceclaw

# Backend
cd voice-server
poetry install

# Frontend
cd ../web-client
npm install
```

### 配置

```bash
cd voice-server
cp .env.example .env
```

编辑 `.env`：

```env
# OpenClaw Gateway
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=your_token_here  # 可选
OPENCLAW_MODEL=openclaw

# Server
HOST=127.0.0.1
PORT=8765

# Audio
SAMPLE_RATE=16000
```

### 运行

```bash
# 终端 1: 后端
cd voice-server
poetry run uvicorn src.main:app --reload --port 8765

# 终端 2: 前端
cd web-client
npm run dev
```

### 验证

```bash
curl http://localhost:8765/health
# {"ok": true}
```

## API 文档

### HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | 健康检查 |
| POST | `/stt` | 语音转文字 |
| POST | `/tts` | 文字转语音 |

### WebSocket Protocol

**Endpoint**: `ws://localhost:8765/ws/voice`

#### 客户端 → 服务器

```typescript
// 发送音频（base64 encoded 16-bit PCM, 16kHz）
{
  "type": "audio",
  "data": "<base64_audio>"
}

// 发送文本（绕过 STT）
{
  "type": "text",
  "text": "你好"
}
```

#### 服务器 → 客户端

```typescript
// STT 结果
{
  "type": "transcript",
  "text": "你好",
  "language": "Chinese"
}

// 流式响应开始
{
  "type": "response_start"
}

// 流式文本块
{
  "type": "response_chunk",
  "text": "你好"
}

// TTS 音频（句子级）
{
  "type": "audio",
  "data": "<base64_audio>"
}

// 流式响应结束
{
  "type": "response_end",
  "text": "完整响应文本"
}

// 完成
{
  "type": "done"
}

// 错误
{
  "type": "error",
  "text": "错误信息"
}
```

详细 API 文档见 [docs/api.md](docs/api.md)。

## 开发

### 项目结构

```
voiceclaw/
├── voice-server/           # Python 后端
│   ├── src/
│   │   ├── config.py       # 配置管理
│   │   ├── main.py         # FastAPI 入口
│   │   ├── stt/            # Qwen3-ASR
│   │   ├── tts/            # Qwen3-TTS
│   │   ├── gateway/        # OpenClaw Gateway 客户端
│   │   └── ws/             # WebSocket 处理
│   └── tests/              # 测试
│
├── web-client/             # React 前端
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   ├── hooks/          # React Hooks
│   │   └── App.tsx         # 主应用
│   └── package.json
│
└── docs/                   # 文档
```

### 测试

```bash
cd voice-server
poetry run pytest -v
```

### 代码风格

```bash
poetry run ruff check src/ --fix
poetry run mypy src/
```

## 性能

| 指标 | 目标值 | 实测 |
|------|--------|------|
| STT 延迟 | < 100ms | ~70ms |
| TTS 延迟 | < 200ms | ~150ms |
| 首句 TTS | < 500ms | ~300ms |
| 端到端延迟 | < 500ms | ~400ms* |

*包含 Gateway LLM 响应时间

## Roadmap

- [ ] Silero VAD 替换能量检测
- [ ] 打断功能
- [ ] 多说话人区分
- [ ] 语音活动检测可视化
- [ ] 移动端支持

## License

MIT

## 相关项目

- [OpenClaw](https://github.com/openclaw/openclaw) - AI Agent 框架
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) - 语音识别
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - 语音合成
- [MLX](https://github.com/ml-explore/mlx) - Apple Silicon 推理框架
