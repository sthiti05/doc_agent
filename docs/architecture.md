# Doc Agent — Architecture

This document describes the conceptual architecture of the Doc Agent, the key design patterns used, and how the modules interact during a documentation run.

---

## High-Level Flow

```
User (CLI)
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│  main.py                                                     │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐ │
│  │ argparse     │──▶│ asyncio.run()    │──▶│ Print result │ │
│  │ (parse args) │   │ run_doc_agent()  │   │ to stdout    │ │
│  └──────────────┘   └────────┬─────────┘   └──────────────┘ │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  agent.py                                                    │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐ │
│  │ get_model()  │──▶│ create_deep_agent│──▶│ agent.ainvoke│ │
│  │ (LLM select) │   │ (build agent)    │   │ (run audit)  │ │
│  └──────────────┘   └──────────────────┘   └──────┬───────┘ │
└──────────────────────────────────────────────────┼──────────┘
                                                    │
                                                    ▼
                               ┌──────────────────────────────────────────────┐
                               │  Deep Agent (DeepAgents Framework)           │
                               │  ┌────────────────────────────────────────┐  │
                               │  │ Tool inventory:                       │  │
                               │  │  • write_todos — task planning        │  │
                               │  │  • ls — list directory contents        │  │
                               │  │  • read_file — read file contents      │  │
                               │  │  • write_file — write/create files     │  │
                               │  │  • edit_file — edit existing files     │  │
                               │  │  • glob — pattern-based file search    │  │
                               │  │  • grep — text search within files     │  │
                               │  └────────────────────────────────────────┘  │
                               │  • Backend: FilesystemBackend(root_dir)     │
                               │  • System prompt: DOC_INSTRUCTIONS          │
                               │  • Explores → Plans → Writes docs/         │
                               └──────────────────────────────────────────────┘
```

---

## Module Breakdown

### 1. `main.py` — CLI Entry Point

**Responsibility**: Parse command-line arguments, bootstrap async execution, and display results.

**Data flow**:
1. User runs `python main.py <directory> [--instructions <text>]`
2. `argparse.ArgumentParser` parses the positional `directory` argument (defaults to `"."`) and optional `--instructions` / `-i` flag
3. The module prints a styled ASCII banner showing the target directory and any custom instructions
4. `load_dotenv()` loads environment variables from `.env`
5. `asyncio.run(run_doc_agent(...))` launches the async documentation agent
6. On success, the agent's final response is printed to stdout
7. On failure, the exception is printed to stderr and the process exits with code 1

**Key behaviors**:
- **UTF-8 Windows fix**: If running on Windows, `sys.stdout.reconfigure(encoding="utf-8")` and `sys.stderr.reconfigure(encoding="utf-8")` are called, ensuring emoji (📝, 🚀, ❌) and Markdown symbols render correctly in `cmd.exe` and PowerShell.
- **`.env` loading**: `load_dotenv()` is called at module import time, before any agent startup logic, so all API keys are available when `agent.py` initializes the LLM.

### 2. `agent.py` — Agent Orchestration & LLM Routing

**Responsibility**: Select the appropriate LLM, create the deep agent with a filesystem-backed toolset, and invoke it against the target codebase.

```
run_doc_agent(target_directory, specific_instructions)
  ├── get_model()                  → ChatOpenAI | ChatGoogleGenerativeAI
  ├── create_deep_agent(
  │       model,
  │       backend=FilesystemBackend(root_dir, virtual_mode=False),
  │       system_prompt=DOC_INSTRUCTIONS
  │   )
  └── agent.ainvoke({messages: [...]}) → result
```

**`get_model()` — LLM Routing Logic**:

```
get_model()
  │
  ├── 1. Read env vars: OPENAI_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY
  │
  ├── 2. Strip whitespace from all found keys
  │
  ├── 3. Is GOOGLE_API_KEY / GEMINI_API_KEY set?
  │     YES → Determine model name:
  │       MODEL_NAME → GOOGLE_MODEL_NAME → "gemini-1.5-flash" (default)
  │     → ChatGoogleGenerativeAI(model, google_api_key)
  │
  ├── 4. Is OPENAI_API_KEY set?
  │     │
  │     ├── 4a. Does key match DeepSeek format (sk- + 32 hex chars)?
  │     │     YES → Auto-set base_url="https://api.deepseek.com"
  │     │           Auto-set model="deepseek-chat"
  │     │           → ChatOpenAI(model, api_key, base_url)
  │     │
  │     └── 4b. NO → Use configured OPENAI_BASE_URL (if any)
  │                  Use configured MODEL_NAME or default "gpt-4o-mini"
  │                  → ChatOpenAI(model, api_key, base_url)
  │
  └── 5. No key found → raise ValueError
```

**Key behaviors**:
- **Priority**: Google Gemini takes precedence over OpenAI-compatible. If both keys are set, Gemini is used.
- **Whitespace sanitization**: Both `openai_key` and `google_key` are trimmed with `.strip()` to guard against accidental leading/trailing spaces in `.env` files.
- **DeepSeek auto-detection**: If the key structure matches `sk-` followed by exactly 32 hexadecimal characters, the agent treats it as a DeepSeek key. It automatically overrides the base URL to `"https://api.deepseek.com"` (unless a non-OpenAI URL is explicitly set) and the model to `"deepseek-chat"`.
- **Model name resolution**: `MODEL_NAME` is the universal override; `GOOGLE_MODEL_NAME` is Gemini-specific. This allows the user to configure the provider via key selection and the model independently.
- **`FilesystemBackend`** is instantiated with `root_dir=target_directory` and `virtual_mode=False`. This means all file operations performed by the agent (like `read_file`, `write_file`, `glob`) directly touch the real filesystem within the target directory's scope.

### 3. System Prompt (`DOC_INSTRUCTIONS`)

The system prompt embedded in `agent.py` instructs the LLM to:

1. **Plan the audit** using the `write_todos` tool.
2. **Explore** entry points and code structure via `ls`, `read_file`, `glob`, `grep`.
3. **Generate documentation** in the `docs/` folder:
   - `docs/overview.md` — project summary, features, folder structure.
   - `docs/architecture.md` — design explanation and module interactions.
   - `docs/api_reference.md` — detailed class, function, and workflow docs.
4. **Remain thorough** — no placeholder text, all documentation must be polished and detailed.
5. **Always write inside `docs/`** — the prompt explicitly forbids writing documentation files outside the `docs/` directory.

### 3. System Prompt (`DOC_INSTRUCTIONS`)

The system prompt embedded in `agent.py` instructs the LLM to:

1. **Plan the audit** using the `write_todos` tool.
2. **Explore** entry points and code structure via `ls`, `read_file`, `glob`, `grep`.
3. **Generate documentation** in the `docs/` folder:
   - `docs/overview.md` — project summary, features, folder structure.
   - `docs/architecture.md` — design explanation and module interactions.
   - `docs/api_reference.md` — detailed class, function, and workflow docs.
4. **Remain thorough** — no placeholder text, all documentation must be polished and detailed.
5. **Always write inside `docs/`** — the prompt explicitly forbids writing documentation files outside the `docs/` directory.

---

## Design Patterns

### Agent Pattern (DeepAgents)

The project uses **DeepAgents** (`create_deep_agent`), a framework that wraps an LLM into an autonomous agent capable of:

- Calling tools (read/write files, search, glob, grep)
- Planning multi-step objectives with `write_todos`
- Chaining multiple steps to fulfill a complex objective (observe → reason → act → observe)
- Iterating and self-correcting based on intermediate results

This is the core pattern — the LLM is **not** prompted to generate documentation in one shot. Instead, it is given a toolset and asked to **explore, plan, and write** iteratively, just as a human technical writer would.

### Router Pattern (Model Selection)

`get_model()` implements a **priority-based router**:

1. Google Gemini (highest priority — checked first)
2. OpenAI-compatible (fallback — includes standard OpenAI, DeepSeek, and custom endpoints)
3. Error: no API key configured

Within the OpenAI-compatible branch, a **DeepSeek auto-detection sub-router** overrides default base URL and model name when a DeepSeek-format key is detected, removing the need for manual configuration.

### CLI Argument Pattern (argparse)

Uses Python's standard `argparse` module with:
- One **positional argument** (`directory`) — the target codebase path, defaults to `"."`
- One **optional flag** (`--instructions` / `-i`) — custom guidance for the documentation agent

### Filesystem Sandbox Pattern

`FilesystemBackend(root_dir=target_directory, virtual_mode=False)` restricts all file read/write operations to the target directory and its subdirectories. This provides safety against accidental modifications outside the project, while still allowing full read/write access within the target.

### Async Wrapper Pattern

Since DeepAgents' `ainvoke()` is async, `main.py` wraps the call with `asyncio.run()`. This bridges the synchronous CLI entry point to the async agent execution model cleanly.

---

## Execution Flow in Detail

### Step-by-Step Runtime Walkthrough

1. **User invokes CLI**: `python main.py /path/to/project -i "Focus on API"`
2. **main.py**:
   - Reconfigures stdout to UTF-8 if on Windows
   - Loads `.env` via `load_dotenv()`
   - Parses arguments → `directory="/path/to/project"`, `instructions="Focus on API"`
   - Prints banner with config info
   - Calls `asyncio.run(run_doc_agent("/path/to/project", "Focus on API"))`
3. **agent.py** (`run_doc_agent`):
   - Prints `"🚀 Initializing Deep Documentation Agent for: /path/to/project"`
   - Calls `get_model()` → resolves LLM provider
   - Creates agent with `FilesystemBackend(root_dir="/path/to/project")` and `DOC_INSTRUCTIONS` system prompt
   - Builds user prompt and calls `agent.ainvoke({...})`
4. **Deep Agent** (autonomous loop):
   - Receives user prompt + system instructions
   - Plans audit using `write_todos`
   - Explores codebase with `ls`, `glob`, `read_file`, `grep`
   - Analyzes module structure and dependencies
   - Writes `docs/overview.md`, `docs/architecture.md`, `docs/api_reference.md`
   - Returns final response to caller
5. **main.py**: Prints agent's final message and success banner

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Optional* | — | API key for OpenAI or DeepSeek |
| `OPENAI_BASE_URL` | Optional | — | Base URL override (e.g., `https://api.deepseek.com`) |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Optional* | — | API key for Google Gemini |
| `MODEL_NAME` | Optional | `"gpt-4o-mini"` (OpenAI) / `"gemini-1.5-flash"` (Gemini) | Override model name for the active provider |
| `GOOGLE_MODEL_NAME` | Optional | `"gemini-1.5-flash"` | Specific model name for Gemini provider |

\* At least one of `OPENAI_API_KEY` or `GOOGLE_API_KEY` / `GEMINI_API_KEY` must be set.

---

## Threading & Concurrency Model

- **main.py** runs synchronously with a single call to `asyncio.run()`, which creates a single event loop.
- **agent.py** uses `await agent.ainvoke()` — the deep agent's execution is async but single-threaded from the Python perspective.
- Inside the **Deep Agent**, the LLM makes sequential tool calls and LLM inferences. There is no parallelism within a single agent invocation.
- Overall, the system is **single-threaded, asynchronous** — appropriate for I/O-bound operations like file reads, LLM API calls, and file writes.

---

## Security & Isolation

- **Filesystem scope**: The `FilesystemBackend` restricts all file operations to the `root_dir` provided. The agent cannot read or write files outside the target directory.
- **API keys**: Loaded from `.env` file (which is `.gitignore`-listed) or environment variables — never hard-coded.
- **LLM communication**: All API calls are made over HTTPS to the configured LLM provider. No data is stored or logged by the tool itself.

