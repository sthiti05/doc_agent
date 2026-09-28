# Doc Agent — API Reference

This document provides detailed reference for every function, module, and configuration surface in the Doc Agent codebase.

---

## Module: `main.py`

**Path**: `main.py`

The CLI entry point. Parses arguments, loads environment variables, and launches the async documentation agent.

### Imports

```python
import argparse
import asyncio
import sys
from dotenv import load_dotenv
from agent import run_doc_agent
```

### Top-Level Module Statements

#### UTF-8 Console Encoding (Windows)

```python
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
```

Reconfigures stdout/stderr to UTF-8 on Windows so emoji and Markdown characters display correctly in `cmd.exe` and PowerShell.

#### Environment Loading

```python
load_dotenv()
```

Loads environment variables from the `.env` file in the current working directory at import time, so API keys are available before `main()` runs.

### Functions

#### `main()`

The main entry point for the CLI tool. Declared as the `doc-agent` console script in `pyproject.toml`.

**Signature**:
```python
def main() -> None
```

**Behavior**:
1. Creates an `argparse.ArgumentParser` with program name `doc-agent`, a provider-aware description, and `RawDescriptionHelpFormatter`.
2. Configures five arguments:
   - `directory` (positional, optional): Target codebase path. Defaults to `"."`.
   - `--instructions` / `-i`: Custom guidance text for the agent. Defaults to `""`.
   - `--api-key` / `-k`: Explicit LLM API key (OpenAI, Gemini, or DeepSeek). Defaults to `None`.
   - `--model` / `-m`: Model name override (e.g. `gpt-4o`, `gemini-1.5-pro`, `deepseek-chat`). Defaults to `None`.
   - `--base-url`: Custom OpenAI-compatible API base URL. Defaults to `None`.
3. Prints a styled ASCII banner showing the target directory and any supplied instructions, model override, or base URL.
4. Calls `asyncio.run(run_doc_agent(directory, instructions, api_key=args.api_key, model_name=args.model, base_url=args.base_url))`.
5. On success: Prints a success banner and the agent's final response.
6. On failure: Prints the exception to stderr and calls `sys.exit(1)`.

**Example**:
```bash
doc-agent ./my-project --api-key KEY --model gpt-4o --instructions "Focus on API endpoints"
```

---

## Module: `agent.py`

**Path**: `agent.py`

Core module that selects the LLM provider, builds the deep agent with a scoped filesystem backend and security deny-rules, and streams the agent's execution.

### Imports

```python
import os
import asyncio
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import FilesystemBackend
```

- `os` — Reading environment variables for API keys and configuration.
- `asyncio` — Supplies `asyncio.run` usage; `run_doc_agent` is an async generator-driven coroutine.
- `ChatOpenAI` — LangChain's OpenAI-compatible chat model wrapper (used for OpenAI, DeepSeek, and Azure serverless).
- `create_deep_agent`, `FilesystemPermission` — Agent factory and the capability used to deny reads of sensitive files.
- `FilesystemBackend` — Provides the filesystem tool implementations (read, write, glob, grep, etc.) to the agent.

### Constants

#### `DOC_INSTRUCTIONS`

```python
DOC_INSTRUCTIONS: str = """You are an expert technical writer and software architect.
Your mission is to audit the provided codebase, understand its layout, core modules, architecture, and functions, and write high-quality markdown documentation.

CRITICAL DIRECTIVES:
1. ALWAYS write all generated documentation files inside the `docs/` folder (relative to your workspace root). If the `docs/` folder does not exist, create it using your file tools. Do not write any documents outside the `docs/` folder.
2. First, use 'write_todos' to plan which modules, directories, and files you need to audit.
3. Read the entry points and code structure (using 'ls', 'read_file', 'glob', etc.) to understand functional dependencies.
4. Create clear, concise, and structured documentation files. Recommended files to write inside the `docs/` folder:
   - `docs/overview.md`: Summary of the project, features, and folder structure.
   - `docs/architecture.md`: Conceptual explanation of design, modules, and how they interact.
5. Do not leave placeholder text.
6. NEVER read, open, or reference the `.env` or `.gitignore` files. These files contain sensitive configuration and must be completely ignored.
"""
```

The system prompt given to the LLM-powered agent. It establishes the role (expert technical writer & software architect), requires that all output be written inside the `docs/` folder, directs the agent to plan with `write_todos` and explore with `ls`/`read_file`/`glob`, and forbids reading `.env` / `.gitignore` at both the prompt level and via permissions.

### Functions

#### `run_doc_agent()`

Initializes and invokes the deep agent to audit a codebase and write documentation, streaming progress to the console.

**Signature**:
```python
async def run_doc_agent(
    target_directory: str,
    specific_instructions: str = "",
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
) -> str
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_directory` | `str` | — | Absolute or relative path to the codebase root to document |
| `specific_instructions` | `str` | `""` | Optional custom guidance appended to the agent prompt |
| `api_key` | `str \| None` | `None` | Explicit LLM API key (OpenAI, Gemini, or DeepSeek) |
| `model_name` | `str \| None` | `None` | Model name override, e.g. `gpt-4o`, `gemini-1.5-pro`, `deepseek-chat` |
| `base_url` | `str \| None` | `None` | Custom OpenAI-compatible API base URL |

The last three parameters are keyword-only.

**Returns**:
| Type | Description |
|------|-------------|
| `str` | The content of the final model message (the agent's concluding response) |

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | When no API key can be resolved (propagated from `get_model()`) |
| Various | Any LangChain or DeepAgents exceptions during agent execution |

**Behavior**:
1. Resolves and prints the absolute target directory (`os.path.abspath`).
2. Calls `get_model(api_key=..., model_name=..., base_url=...)` to obtain the appropriate LangChain chat model.
3. Builds a `FilesystemPermission` deny rule (`operations=["read"]`, `mode="deny"`) covering `/.env`, `/**/.env`, `/.gitignore`, and `/**/.gitignore` to block sensitive-file reads across path-matching styles.
4. Creates the deep agent with:
   - The selected model.
   - `FilesystemBackend(root_dir=abs_target_dir, virtual_mode=True)` — file operations scoped to the target and resolved virtually.
   - The `DOC_INSTRUCTIONS` system prompt.
   - `permissions=[denied_files]`.
5. Builds a user prompt telling the agent to audit the current workspace and write docs into `docs/`, appending `specific_instructions` if provided.
6. Iterates `async for event in agent.astream({...})` and, for each event, prints:
   - **Tool outputs** under a `💻 Tool [...]` label with long outputs truncated to ~120 chars.
   - **Model responses** under a `🧠 Agent response:` label.
   - **Tool calls** under a `🔍 Agent decided to run tool [...]` label with their arguments.
7. Captures the last non-empty model message as the final answer and returns it.

**Example**:
```python
result = await run_doc_agent(
    "/home/user/project",
    "Highlight security concerns",
    api_key="sk-...",
    base_url="https://api.deepseek.com",
)
print(result)
```

---

#### `get_model()`

Resolves and returns the appropriate LangChain chat model based on API keys and configuration, with a **CLI flag > environment variable > default** priority for each value.

**Signature**:
```python
def get_model(
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
) -> ChatOpenAI | ChatGoogleGenerativeAI
```

All parameters are keyword-only.

**Returns**:
| Return Type | Condition |
|------------|-----------|
| `ChatGoogleGenerativeAI` | When a Gemini key resolves (and no Azure key is present) |
| `ChatOpenAI` | When an OpenAI/DeepSeek key resolves, or when using Azure serverless |

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` (via `ChatOpenAI`) | When neither an OpenAI/DeepSeek key nor a Gemini key nor Azure credentials can be resolved |

**Behavior**:
1. **Resolve keys**: `api_key` (CLI) wins over `OPENAI_API_KEY`. Gemini keys (`GOOGLE_API_KEY` / `GEMINI_API_KEY`) are only read when no explicit CLI key was passed. All keys are `.strip()`-ed.
2. **Resolve base URL**: `base_url` (CLI) > `OPENAI_BASE_URL` env var. `.strip()`-ed.
3. **Resolve model name**: `model_name` (CLI) > `MODEL_NAME` env var.
4. **Azure AI serverless branch** — if `AZURE_OPENAI_API_KEY` is set:
   - Builds `base_url = f"{endpoint}/openai/deployments/{deployment}"` and injects `api-version` (default `2024-02-01`) and `api-key` headers via `ChatOpenAI`.
   - Returns `ChatOpenAI(model=deployment, ...)`.
5. **Google Gemini branch** — if a Gemini key resolved:
   - Model: `model_name` (CLI) > `GOOGLE_MODEL_NAME` > `"gemini-1.5-flash"`.
   - Returns `ChatGoogleGenerativeAI(model=resolved_model, google_api_key=google_key)`.
6. **OpenAI / DeepSeek branch** — if `openai_key` resolved:
   - **DeepSeek auto-detection**: if the key body (after stripping a leading `sk-`) is exactly 32 hex characters, it is treated as DeepSeek:
     - Redirects `base_url` to `https://api.deepseek.com` when no base URL is set or when it still references `openai.com`.
     - Sets `model_name` to `deepseek-chat` when unset or still the default `gpt-4o-mini`.
   - Default model is `gpt-4o-mini`.
   - Returns `ChatOpenAI(model=resolved_model, api_key=openai_key, base_url=base_url or None)`.

> Provider precedence: Azure is checked first, then Gemini, then OpenAI/DeepSeek. If both a Gemini key and an OpenAI/DeepSeek key are present (and no CLI key is given), Gemini wins.

---

## Configuration Files

### `.env`

**Path**: `.env`

Environment variable configuration file. Not committed to git, and explicitly denied to the agent by the `FilesystemPermission` deny rule.

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for OpenAI or DeepSeek |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible base URL |
| `GOOGLE_API_KEY` | API key for Google Gemini |
| `GEMINI_API_KEY` | Alias for `GOOGLE_API_KEY` |
| `MODEL_NAME` | Model-name override for the active provider |
| `GOOGLE_MODEL_NAME` | Gemini-specific model name (default `gemini-1.5-flash`) |
| `AZURE_OPENAI_API_KEY` | Enables the Azure AI serverless path |
| `AZURE_OPENAI_ENDPOINT` | Azure endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure deployment/model name |
| `AZURE_OPENAI_API_VERSION` | Azure API version (default `2024-02-01`) |

### `pyproject.toml`

**Path**: `pyproject.toml`

Project configuration used by `pip` and `uv`.

#### Core Fields

| Field | Value |
|-------|-------|
| `name` | `"doc-agent"` |
| `version` | `"0.1.0"` |
| `description` | `"AI-powered CLI tool that automatically generates markdown documentation for any codebase."` |
| `readme` | `"README.md"` |
| `requires-python` | `">=3.13"` |
| `license` | `"MIT"` |

#### Console Script

```toml
[project.scripts]
doc-agent = "main:main"
```

Installs the `doc-agent` command, which calls `main.main()`.

#### Packaging

```toml
[tool.setuptools]
py-modules = ["agent", "main"]
```

Declares `agent` and `main` as top-level modules.

#### Dependencies

| Package | Version Constraint | Purpose |
|---------|-------------------|---------|
| `adapter` | `>=0.1` | Adapter-pattern utilities |
| `deepagents` | `>=0.6.2` | Agent orchestration framework with filesystem backends |
| `deepseek` | `>=1.0.0` | DeepSeek API client support |
| `langchain` | `>=1.3.1` | Core LLM abstraction framework |
| `langchain-google-genai` | `>=4.2.2` | Google Gemini provider integration |
| `langchain-mcp-adapters` | `>=0.2.2` | MCP protocol adapters for LangChain |
| `langchain-openai` | `>=1.2.1` | OpenAI-compatible provider integration |
| `mcp` | `>=1.27.1` | Model Context Protocol SDK |
| `python-dotenv` | `>=1.0.0` | Load `.env` files at startup |

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Documentation process completed successfully |
| `1` | Error occurred during agent execution (exception caught in `main()`) |

## Type Reference

### Return Types

| Type | Description | Source Module |
|------|-------------|---------------|
| `ChatOpenAI` | LangChain's OpenAI-compatible chat model instance | `langchain_openai` |
| `ChatGoogleGenerativeAI` | LangChain's Google Gemini chat model instance | `langchain_google_genai` |
| `str` | The agent's final response content | — |

### Internal Types (DeepAgents)

| Type | Description |
|------|-------------|
| `FilesystemBackend` | A DeepAgents backend that provides filesystem tools (ls, read, write, edit, glob, grep) operating on a real directory |
| `DeepAgent` | The agent object created by `create_deep_agent()`, which wraps an LLM with tool access and an autonomous reasoning loop |


## Configuration: `.python-version`

**Path**: `/.python-version`

Contains `3.13`, specifying the required Python version for `uv` and related tooling.

---

## External Dependencies (Key APIs)

### DeepAgents: `create_deep_agent()`

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model,                          # ChatOpenAI | ChatGoogleGenerativeAI
    backend=FilesystemBackend(
        root_dir="/path/to/target",
        virtual_mode=True
    ),
    system_prompt="..."              # Instructions passed to the agent
)
```

**Key Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | LLM | LangChain-compatible chat model instance |
| `backend` | `FilesystemBackend` | Filesystem access controller scoped to `root_dir` |
| `system_prompt` | `str` | System-level instructions for the agent's behavior |

### FilesystemBackend

```python
FilesystemBackend(root_dir="/path", virtual_mode=True)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root_dir` | `str` | — | Root directory that the agent is allowed to read/write |
| `virtual_mode` | `bool` | `True` | When `False`, operations hit the real filesystem |

---

## Workflow: End-to-End Execution Trace

```
1. User runs `python main.py /my/codebase -i "Focus on APIs"`
2. main.py:
   a. Reconfigures stdout to UTF-8 (Windows)
   b. Loads .env via load_dotenv()
   c. Parses args → directory="/my/codebase", instructions="Focus on APIs"
   d. Calls asyncio.run(run_doc_agent("/my/codebase", "Focus on APIs"))
3. agent.py:
   a. run_doc_agent() calls get_model()
   b. get_model() reads env vars, selects provider, returns model
   c. create_deep_agent() is called with model + FilesystemBackend
   d. Agent is invoked with prompt:
        "Please audit the codebase located at '/my/codebase'.
         Analyze its contents and write comprehensive markdown documentation for it.
         Remember, you MUST save all documentation files inside the `/docs` folder.
         Additional guidance: Focus on APIs"
   e. The deep agent autonomously:
      - Lists files in /my/codebase
      - Reads source code
      - Plans and writes docs/overview.md, docs/architecture.md, docs/api_reference.md
4. Result is printed to stdout
```
