# Doc Agent — Overview

**Doc Agent** is an autonomous CLI documentation generator that audits a codebase and produces high-quality Markdown documentation. It leverages **LangChain** and the **DeepAgents** framework to deploy an LLM-powered "deep agent" that explores source code, analyzes module structure, and writes polished documentation files into a `docs/` folder.

---

## Features

- **Autonomous Codebase Auditing**  
  The agent recursively explores the target directory, understands file dependencies, maps out architecture, and generates structured documentation without manual intervention.

- **Multi-LLM Support**  
  Supports **OpenAI-compatible models** (GPT-4o-mini, DeepSeek Chat, custom endpoints) and **Google Gemini** models out of the box. The agent auto-selects the provider based on available API keys.

- **Smart DeepSeek Detection**  
  Automatically recognizes DeepSeek API keys by their format (`sk-` followed by 32 hex characters) and self-heals the base URL and model name — no manual configuration required.

- **Custom Instructions**  
  Pass optional `--instructions` / `-i` flags to provide specific guidance (e.g., "Focus on API endpoints", "Highlight security considerations").

- **UTF-8 Console Support**  
  Automatically reconfigures Windows console encoding so emoji and Markdown characters display correctly in `cmd.exe` and PowerShell.

- **Filesystem Sandboxing**  
  Uses `FilesystemBackend` from DeepAgents to restrict all file operations to the target directory, preventing accidental writes outside the project scope.

- **Industry-Standard Tooling**  
  Built on LangChain's abstraction layer, enabling seamless switching between LLM providers and integration with the Model Context Protocol (MCP).

---

## Project Structure

```
.
├── .env                      # API keys and base URL configuration
├── .gitignore                # Excludes __pycache__, .venv, .env
├── .python-version           # Specifies Python 3.13
├── pyproject.toml            # Project metadata and dependency declarations
├── README.md                 # Project README (placeholder)
├── main.py                   # CLI entry point with argument parsing
├── agent.py                  # Core agent initialization and LLM routing logic
├── uv.lock                   # Dependency lockfile (managed by uv)
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
| **Filesystem Access** | DeepAgents `FilesystemBackend` |
| **CLI Parsing** | `argparse` (stdlib) |
| **Environment Management** | `python-dotenv` (`load_dotenv`) |
| **Package Manager** | `uv` (with `uv.lock` lockfile) |
| **MCP Protocol** | `mcp`, `langchain-mcp-adapters` |

---

## Dependencies (from `pyproject.toml`)

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `adapter` | >=0.1 | Adapter pattern utilities |
| `deepagents` | >=0.6.2 | Agent orchestration framework with filesystem backends |
| `deepseek` | >=1.0.0 | DeepSeek API support |
| `langchain` | >=1.3.1 | Core LLM abstraction framework |
| `langchain-google-genai` | >=4.2.2 | Google Gemini provider for LangChain |
| `langchain-mcp-adapters` | >=0.2.2 | MCP protocol adapters for LangChain |
| `langchain-openai` | >=1.2.1 | OpenAI-compatible provider for LangChain |
| `mcp` | >=1.27.1 | Model Context Protocol toolkit |
| `python-dotenv` | (implicit via `deepagents`) | Load `.env` files at startup |

---

## Quick Start

### Prerequisites

- Python 3.13 or later
- An API key from one of the supported LLM providers (OpenAI, DeepSeek, or Google Gemini)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd doc-agent

# Create a virtual environment and install dependencies
uv venv
uv sync
```

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
