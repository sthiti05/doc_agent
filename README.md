# 📄 doc-agent

> AI-powered CLI tool that automatically generates comprehensive markdown documentation for any codebase.

Point `doc-agent` at any project directory and it will autonomously explore the code, understand its architecture, and write structured markdown docs — powered by OpenAI, Google Gemini, or DeepSeek.

---

## ✨ Features

- 🤖 **Agentic** — the AI reads your files, plans what to document, and writes everything autonomously
- 📁 **Any codebase** — works on Python, JavaScript, TypeScript, Go, or any language
- 🌐 **Multi-provider** — supports OpenAI, Google Gemini, and DeepSeek (auto-detected from your key)
- 📝 **Structured output** — generates `overview.md`, `architecture.md`, `api_reference.md` inside a `docs/` folder
- 🔒 **Safe** — never reads `.env` or `.gitignore` files; scoped to your target directory only

---

## 🚀 Installation

### From PyPI (recommended)

```bash
pip install doc-agent
```

### From source

```bash
git clone https://github.com/your-username/doc-agent
cd doc-agent
pip install -e .
```

---

## 🔑 API Key Setup

`doc-agent` needs an LLM API key. You have three options (in order of priority):

### Option 1 — CLI flag (easiest, no config needed)

```bash
doc-agent ./my-project --api-key YOUR_API_KEY
```

### Option 2 — Environment variable

```bash
# Windows
set OPENAI_API_KEY=your-key-here

# macOS / Linux
export OPENAI_API_KEY=your-key-here
```

### Option 3 — `.env` file

Create a `.env` file in your working directory:

```env
OPENAI_API_KEY=your-key-here
```

---

## 🤖 Supported AI Providers

| Provider | Key Variable | Auto-detected? |
|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | ✅ Yes |
| **Google Gemini** | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | ✅ Yes |
| **DeepSeek** | `OPENAI_API_KEY` (with DeepSeek key format) | ✅ Yes — auto-redirects |

> **DeepSeek**: Just pass your DeepSeek key — the tool auto-detects it by the key format and sets the correct base URL automatically.

---

## 📖 Usage

### Basic — document any project

```bash
doc-agent /path/to/your/project
```

### With custom instructions

```bash
doc-agent ./my-api --instructions "Focus on the REST API endpoints and data models"
```

### Specify a model

```bash
doc-agent ./my-project --api-key YOUR_KEY --model gpt-4o
doc-agent ./my-project --api-key YOUR_KEY --model gemini-1.5-pro
doc-agent ./my-project --api-key YOUR_KEY --model deepseek-chat
```

### Custom OpenAI-compatible provider

```bash
doc-agent ./my-project \
  --api-key YOUR_KEY \
  --base-url https://your-custom-provider.com/v1 \
  --model custom-model-name
```

### Document the current directory

```bash
cd my-project
doc-agent .
```

---

## ⚙️ All CLI Options

```
usage: doc-agent [-h] [--instructions TEXT] [--api-key KEY] [--model MODEL] [--base-url URL] [directory]

positional arguments:
  directory              Path to the codebase directory to document (default: .)

options:
  -h, --help             Show this help message and exit
  -i, --instructions     Custom guidance for the agent
  -k, --api-key          Your LLM API key (OpenAI, Gemini, or DeepSeek)
  -m, --model            Model name to use (e.g. gpt-4o, gemini-1.5-pro, deepseek-chat)
  --base-url             Custom OpenAI-compatible base URL
```

---

## 📂 Output

All documentation is written to a `docs/` folder **inside your target directory**:

```
your-project/
└── docs/
    ├── overview.md        ← Project summary, features, folder structure
    ├── architecture.md    ← Module design, how components interact
    └── api_reference.md   ← Functions, classes, parameters, return types
```

---

## 🔧 Environment Variables Reference

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI or DeepSeek API key |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Google Gemini API key |
| `MODEL_NAME` | Default model to use |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible base URL |
| `GOOGLE_MODEL_NAME` | Default Gemini model (e.g. `gemini-1.5-pro`) |

---

## 📋 Requirements

- Python 3.13+
- An API key for OpenAI, Google Gemini, or DeepSeek

---

## 📜 License

MIT
