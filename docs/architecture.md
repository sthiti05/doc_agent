# Doc Agent — Architecture

This document describes the conceptual architecture of Doc Agent, the key design patterns used, and how the modules interact during a documentation run.

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
│  ┌──────────────┐   ┌────────────────────┐   ┌──────────┐   │
│  │ get_model()  │──▶│ create_deep_agent  │──▶│ astream  │   │
│  │ (LLM select) │   │ (build agent +     │   │ (stream  │   │
│  │              │   │  permissions)      │   │  events) │   │
│  └──────────────┘   └────────────────────┘   └──────────┘   │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
               ┌──────────────────────────────────────────────┐
               │  Deep Agent (DeepAgents Framework)           │
               │  ┌────────────────────────────────────────┐  │
               │  │ Tools: write_todos · ls · glob         │  │
               │  │        grep · read_file · write/       │  │
               │  │        edit_file                       │  │
               │  └────────────────────────────────────────┘  │
               │  Backend: FilesystemBackend(root_dir,       │
               │           virtual_mode=True)                 │
               │  Permissions: deny reads of .env/.gitignore │
               │  Prompt: DOC_INSTRUCTIONS                    │
               │  Explores → Plans → Writes docs/             │
               └──────────────────────────────────────────────┘
```

---

## Module Breakdown

### 1. `main.py` — CLI Entry Point

**Responsibility**: Parse command-line arguments, bootstrap async execution, and display results.

**Data flow**:
1. At import time, reconfigure stdout/stderr to UTF-8 when running on Windows so emoji and Markdown render correctly in `cmd.exe` / PowerShell.
2. `load_dotenv()` loads environment variables from `.env` (before any agent logic runs).
3. `argparse.ArgumentParser` parses:
   - `directory` (positional, optional) — target codebase path, defaults to `"."`
   - `--instructions` / `-i` — custom guidance text
   - `--api-key` / `-k` — explicit LLM API key
   - `--model` / `-m` — model name override
   - `--base-url` — custom OpenAI-compatible base URL
4. Prints a styled ASCII banner summarizing the configuration.
5. Calls `asyncio.run(run_doc_agent(directory, instructions, api_key=..., model_name=..., base_url=...))`.
6. On success, prints a success banner and the agent's final response.
7. On failure, prints the exception to stderr and calls `sys.exit(1)`.

**Console script**: declared in `pyproject.toml` as `doc-agent = "main:main"`, so the tool is invoked as the `doc-agent` command.

### 2. `agent.py` — Agent Orchestration & LLM Routing

**Responsibility**: Select the appropriate LLM, build the deep agent with a scoped filesystem toolset and security deny-rules, invoke it, and stream activity to the console.

```
run_doc_agent(target_directory, specific_instructions, *,
              api_key=None, model_name=None, base_url=None)
  ├── abs_target_dir = abspath(target_directory)
  ├── model = get_model(api_key=..., model_name=..., base_url=...)
  ├── denied_files = FilesystemPermission(operations=["read"],
  │       paths=["/.env","/**/.env","/.gitignore","/**/.gitignore"],
  │       mode="deny")
  ├── agent = create_deep_agent(
  │       model,
  │       backend=FilesystemBackend(root_dir=abs_target_dir, virtual_mode=True),
  │       system_prompt=DOC_INSTRUCTIONS,
  │       permissions=[denied_files],
  │   )
  └── async for event in agent.astream({messages: [...]}):
        → stream tool outputs, tool calls, and model responses to console
```

**`get_model()` — LLM Routing Logic**:

The function resolves keys, base URL, and model name with a **priority: CLI flag > environment variable > auto-detected default**. The resolution order is:

1. **Resolve keys**: `api_key` (CLI) wins; otherwise read `OPENAI_API_KEY`. Gemine keys (`GOOGLE_API_KEY` / `GEMINI_API_KEY`) are only considered when no explicit CLI key is given.
2. **Strip whitespace** from all resolved keys.
3. **Resolve base URL**: `base_url` (CLI) > `OPENAI_BASE_URL` env var.
4. **Resolve model name**: `model_name` (CLI) > `MODEL_NAME` env var.
5. **Azure AI serverless branch** — if `AZURE_OPENAI_API_KEY` is set:
   - Constructs `base_url = "{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}"`, preserving the standard OpenAI request body (Model-as-a-Service).
   - Injects the `api-version` query param and `api-key` header.
   - Returns a `ChatOpenAI` configured for the deployment.
6. **Google Gemini branch** — if `google_key` is set:
   - Resolves model: `model_name` (CLI) > `GOOGLE_MODEL_NAME` > `"gemini-1.5-flash"`.
   - Returns `ChatGoogleGenerativeAI(model, google_api_key)`.
7. **OpenAI / DeepSeek branch** — if `openai_key` is set:
   - **Auto-detect DeepSeek**: if the key body (after stripping a leading `sk-`) is exactly 32 hex characters, it is treated as DeepSeek. The base URL is redirected to `https://api.deepseek.com` (unless a non-OpenAI URL was explicitly configured) and the model defaults to `deepseek-chat`.
   - Otherwise the resolved model defaults to `gpt-4o-mini` and the configured/default OpenAI base URL is used.
   - Returns `ChatOpenAI(model, api_key, base_url)`.

> **Note on provider precedence**: Gemini is checked *before* the OpenAI-compatible branch, so if both a Gemini key and an OpenAI/DeepSeek key are present, Gemini is used (unless an explicit CLI key selects otherwise).

### 3. System Prompt (`DOC_INSTRUCTIONS`)

The `DOC_INSTRUCTIONS` constant embedded in `agent.py` instructs the LLM to:

1. **Plan the audit** using the `write_todos` tool.
2. **Explore** entry points and code structure via `ls`, `read_file`, `glob`, `grep`.
3. **Write all documentation inside the `docs/` folder** — nothing outside it.
4. Generate structured output: `docs/overview.md` (summary, features, folder structure), plus any additional files determined during the audit.
5. Remain thorough and polished — **no placeholder text**.

### 4. Security Deny-Rules (`FilesystemPermission`)

Uniquely, `run_doc_agent` applies a **deny permission** that blocks the agent from reading sensitive files, in addition to the filesystem scope:

- Paths matched (absolute-style, nested-glob): `/.env`, `/**/.env`, `/.gitignore`, `/**/.gitignore`.
- Operation: `read`, mode: `deny`.

This duplicates the deny rules at the prompt level to handle whatever path-matching strategy the `FilesystemBackend` uses.

---

## Design Patterns

### Agent Pattern (DeepAgents)

The project uses **DeepAgents** (`create_deep_agent`), which wraps an LLM into an autonomous agent capable of:

- Calling tools (read/write/search files)
- Planning multi-step objectives with `write_todos`
- Chaining steps (observe → reason → act → observe)
- Iterating and self-correcting on intermediate results

This is the core pattern — the LLM is **not** asked to generate documentation in one shot. It is given a toolset and instructed to **explore, plan, and write** iteratively, like a human technical writer.

### Router Pattern (Model Selection)

`get_model()` implements a **priority-based router**: Azure → Google Gemini → OpenAI-compatible (OpenAI / DeepSeek / custom). Within the OpenAI-compatible branch, a **DeepSeek auto-detection sub-router** overrides the base URL and model for DeepSeek-format keys.

### CLI Argument Pattern (argparse)

Uses Python's standard `argparse` with one positional argument (`directory`, default `"."`) and four optional flags (`--instructions`, `--api-key`, `--model`, `--base-url`), plus automatic `--help`.

### Filesystem Sandbox Pattern

`FilesystemBackend(root_dir=abs_target_dir, virtual_mode=True)` scopes all file operations to the target project while operating on the real filesystem (virtual path resolution). Combined with the `FilesystemPermission` deny rule, this provides strong isolation and guards against leaking sensitive files.

### Streaming / Observer Pattern

Instead of a single `invoke`, `run_doc_agent` iterates over `agent.astream(...)`. Each event is inspected; tool outputs are summarized and printed, tool calls (name + args) are logged, and model responses are streamed — giving the user live visibility into the agent's reasoning and actions.

### Async Wrapper Pattern

`main.py` bridges the synchronous CLI entry point to the async agent model via `asyncio.run()`.

---

## Execution Flow in Detail

### Step-by-Step Runtime Walkthrough

1. **User invokes CLI**: `doc-agent /path/to/project -i "Focus on API" --api-key KEY`
2. **main.py**:
   - Reconfigures UTF-8 output on Windows
   - Loads `.env` via `load_dotenv()`
   - Parses arguments → `directory`, `instructions`, `api_key`, `model`, `base_url`
   - Prints the config banner
   - Calls `asyncio.run(run_doc_agent(...))`
3. **agent.py** (`run_doc_agent`):
   - Resolves and prints the absolute target directory
   - Calls `get_model()` → returns the appropriate LangChain chat model
   - Builds the `FilesystemPermission` deny rule for `.env` / `.gitignore`
   - Creates the deep agent with the backend, system prompt, and permissions
   - Builds the user prompt (appending custom instructions if any)
   - Streams `astream(...)` events, printing tool outputs, tool calls, and model responses
   - Captures the final model message as the return value
4. **Deep Agent** (autonomous loop):
   - Plans the audit with `write_todos`
   - Explores with `ls`, `glob`, `read_file`, `grep`
   - Analyzes structure and dependencies
   - Writes `docs/overview.md` and related files
   - Returns its final message
5. **main.py**: Prints the success banner and the agent's final response.

---

## Environment Variables

| Variable | Role | Description |
|----------|------|-------------|
| `OPENAI_API_KEY` | Provider key | API key for OpenAI or DeepSeek |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Provider key | API key for Google Gemini |
| `AZURE_OPENAI_API_KEY` | Provider key | Enables the Azure AI serverless (MaaS) path |
| `AZURE_OPENAI_ENDPOINT` | Azure config | Azure endpoint (used with the deployment name) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure config | Azure deployment/model name |
| `AZURE_OPENAI_API_VERSION` | Azure config | API version (default `2024-02-01`) |
| `OPENAI_BASE_URL` | Config | Custom OpenAI-compatible base URL |
| `MODEL_NAME` | Config | Universal model-name override |
| `GOOGLE_MODEL_NAME` | Config | Gemini-specific model-name override (default `gemini-1.5-flash`) |

CLI flags (`--api-key`, `--model`, `--base-url`) always take precedence over the matching environment variables.

---

## Concurrency Model

- **main.py** runs synchronously, invoking a single `asyncio.run()` event loop.
- **agent.py** drives the deep agent via `async for event in agent.astream(...)` — execution is async but single-threaded from Python's perspective.
- Within one agent run, tool calls and LLM inference happen sequentially.
- Overall the system is **single-threaded, asynchronous**, well-suited to I/O-bound work (file access and LLM API calls).

---

## Security & Isolation

- **Filesystem scope**: `FilesystemBackend` restricts all reads/writes to the target `root_dir`.
- **Sensitive-file denial**: A `FilesystemPermission` deny rule prevents the agent from reading `.env` or `.gitignore` files at any nesting depth, regardless of path-matching style.
- **API keys**: Supplied via CLI flags, environment variables, or a `.env` file (git-ignored and denied to the agent) — never hard-coded.
- **LLM communication**: All API calls go over HTTPS to the configured provider.

