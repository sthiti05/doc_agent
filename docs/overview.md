# Doc Agent — Overview

**Doc Agent** is an autonomous, CLI-driven documentation generator. It audits any codebase and produces high-quality Markdown documentation without manual intervention. It is built on **LangChain** and the **DeepAgents** framework, which powers an LLM-driven "deep agent" that explores source code, maps module structure and dependencies, and writes structured documents into a `docs/` folder scoped to the target project.

---

## What It Does

Point `doc-agent` at any project directory and it will:

1. **Plan** the audit using the `write_todos` tool.
2. **Explore** the codebase with filesystem tools (`ls`, `read_file`, `glob`, `grep`).
3. **Analyze** entry points, modules, architecture, and functional dependencies.
4. **Write** polished Markdown documentation (`overview.md`, `architecture.md`, `api_reference.md`) inside the target's `docs/` folder.

The entire process is autonomous — the LLM decides what to read, what to annotate, and what to write, mimicking a human technical writer.

---

## Features

- **Autonomous Codebase Auditing**  
  The agent recursively explores the target directory, understands file dependencies, maps out architecture, and generates structured documentation with no manual intervention.

- **Multi-Provider LLM Support**  
  Supports **OpenAI-compatible** models (GPT, DeepSeek Chat, custom endpoints) and **Google Gemini**. The provider is auto-selected from the available API key or explicitly set via CLI flags. **Azure AI serverless (MaaS)** endpoints are also supported through configuration.

- **DeepSeek Auto-Detection**  
  Recognizes DeepSeek API keys by their format (`sk-` followed by exactly 32 hex characters) and automatically redirects the base URL to `https://api.deepseek.com` and defaults the model to `deepseek-chat` — no manual configuration required.

- **Custom Instructions**  
  Pass an optional `--instructions` / `-i` flag to provide specific guidance (e.g., "Focus on the REST API endpoints and data models").

- **Explicit Model / Endpoint Control**  
  `--model` overrides the model name and `--base-url` targets any OpenAI-compatible endpoint, enabling custom providers.

- **Filesystem Sandboxing & Security**  
  Uses DeepAgents `FilesystemBackend` rooted at the target directory to restrict all file operations to that project. A `FilesystemPermission` deny rule blocks the agent from ever reading `.env` or `.gitignore` files at any depth.

- **Real-Time Execution Feedback**  
  Streams agent activity to the console, showing tool calls, arguments, and intermediate model responses as the audit unfolds.

- **UTF-8 Console Support**  
  Automatically reconfigures Windows console encoding so emoji and Markdown characters render correctly in `cmd.exe` and PowerShell.

- **Industry-Standard Tooling**  
  Built on LangChain's abstraction layer for provider portability and integrates the Model Context Protocol (MCP).

---

## Project Structure

```
.
├── .env                      # Optional API keys and configuration (never read by the agent)
├── .gitignore                # VCS ignore rules (never read by the agent)
├── .python-version           # Specifies Python 3.13
├── pyproject.toml            # Project metadata, dependencies, and [project.scripts] entry point
├── README.md                 # Project README / user guide
├── main.py                   # CLI entry point — argument parsing and bootstrap
├── agent.py                  # Core module — agent orchestration and LLM routing
├── uv.lock                   # Dependency lockfile (managed by uv)
├── doc_agent.egg-info/       # Setuptools build metadata (generated)
├── dist/                     # Build artifacts (generated)
├── .venv/                    # Virtual environment (git-ignored)
├── docs/                     # Generated documentation output folder
└── __pycache__/              # Compiled Python bytecode (git-ignored)
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Runtime** | Python 3.13+ |
| **LLM Framework** | LangChain (`langchain`, `langchain-openai`, `langchain-google-genai`) |
| **Agent Framework** | DeepAgents (`create_deep_agent`) |
| **Filesystem Access** | DeepAgents `FilesystemBackend`, `FilesystemPermission` |
| **CLI Parsing** | `argparse` (standard library) |
| **Environment Management** | `python-dotenv` (`load_dotenv`) |
| **Package Manager** | `uv` (with `uv.lock` lockfile) |
| **MCP Protocol** | `mcp`, `langchain-mcp-adapters` |

---

## Dependencies (from `pyproject.toml`)

| Dependency | Minimum Version | Purpose |
|-----------|-----------------|---------|
| `adapter` | 0.1 | Adapter-pattern utilities |
| `deepagents` | 0.6.2 | Agent orchestration framework with filesystem backends |
| `deepseek` | 1.0.0 | DeepSeek API client support |
| `langchain` | 1.3.1 | Core LLM abstraction framework |
| `langchain-google-genai` | 4.2.2 | Google Gemini provider for LangChain |
| `langchain-mcp-adapters` | 0.2.2 | MCP protocol adapters for LangChain |
| `langchain-openai` | 1.2.1 | OpenAI-compatible provider for LangChain |
| `mcp` | 1.27.1 | Model Context Protocol toolkit |
| `python-dotenv` | 1.0.0 | Load `.env` files at startup |

---

## Quick Start

### Prerequisites

- Python 3.13 or later
- An API key from one of the supported providers (OpenAI, DeepSeek, Google Gemini), or Azure credentials

### Installation

```bash
# From PyPI
pip install doc-agent

# From source
git clone https://github.com/your-username/doc-agent
cd doc-agent
uv venv
uv sync
```

### Document a project

```bash
doc-agent /path/to/your/project
```

### With a key and custom instructions

```bash
doc-agent ./my-api --api-key YOUR_KEY --instructions "Focus on the REST API endpoints and data models"
```

See `docs/architecture.md` for a deep dive into module interactions, and `docs/api_reference.md` for the full function and configuration reference.

### Configuration

Create a `.env` file in the project root with either an OpenAI-compatible key or a Google Gemini key:

```ini
# Option 1: OpenAI / DeepSeek
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Option 2: Google Gemini
GOOGLE_API_KEY=your-gemini-key
GOOGLE_MODEL_NAME=gemini-1.5-flash
```

### Usage

```bash
# Document the current directory
python main.py

# Document a specific codebase
python main.py /path/to/your/project

# Provide custom instructions
python main.py /path/to/your/project -i "Focus on API endpoints and authentication"

# Use a shorter flag alias
python main.py . --i "Document only the core modules"
```

### Output

After a successful run, the agent generates these files inside the `docs/` folder of the target directory:

| File | Contents |
|------|----------|
| `docs/overview.md` | Project summary, feature list, folder structure, technology stack |
| `docs/architecture.md` | Architectural design, module interactions, data flow diagrams |
| `docs/api_reference.md` | Detailed API documentation for every function, class, and module |

---

## Error Handling

If no API key is configured, the tool exits with a clear error message:

```
ValueError: No API key found. Set OPENAI_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY in your .env file.
```

If the agent fails mid-execution, the error is caught in `main()` and printed to stderr with a non-zero exit code.
