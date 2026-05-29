# Doc Agent — API Reference

This document provides detailed documentation for every function, module, and configuration file in the Doc Agent codebase.

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

On Windows, reconfigures the standard output and error streams to use UTF-8 encoding, ensuring emoji characters (📝, 🚀, ❌, 🎉) display correctly in `cmd.exe` and PowerShell. The `try/except` silently handles environments where `reconfigure` is unavailable (e.g., redirected output or older Python versions).

#### Environment Loading

```python
load_dotenv()
```

Loads environment variables from the `.env` file in the current working directory before any other logic runs. This is called at module import time, so API keys are available when `main()` executes.

### Functions

#### `main()`

The main entry point for the CLI tool. Called when `python main.py` is run.

**Signature**:
```python
def main() -> None
```

**Behavior**:
1. Creates an `ArgumentParser` with description `"CLI Documentation Writer - Automate generating beautiful markdown docs for your codebases."`
2. Configures two arguments:
   - `directory` (positional, optional): Path to the codebase to document. Defaults to `"."`.
   - `--instructions` / `-i` (optional): Custom guidance text for the agent.
3. Prints a styled ASCII banner showing the target directory and any custom instructions.
4. Calls `asyncio.run(run_doc_agent(directory, instructions))`.
5. On success: Prints `"🎉 Documentation Process Completed successfully!"` and the agent's final response.
6. On failure: Prints the exception to stderr and calls `sys.exit(1)`.

**Example**:
```bash
python main.py /home/user/my-project -i "Focus on API endpoints"
```

**Full output example**:
```
====================================================
         📝 CLI DOCUMENTATION WRITER 📝             
====================================================
Target Directory: /home/user/my-project
Custom Instructions: Focus on API endpoints
====================================================

🚀 Initializing Deep Documentation Agent for: /home/user/my-project
🤖 Using OpenAI-compatible Model: gpt-4o-mini (Base URL: default)
... [agent runs and generates docs] ...

====================================================
🎉 Documentation Process Completed successfully!
====================================================
[agent's final response]
```

---

## Module: `agent.py`

**Path**: `agent.py`

Core module that selects the LLM provider, builds the deep agent, and invokes it against the target codebase.

### Imports

```python
import os
import asyncio
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
```

- `os` — Reading environment variables for API keys and configuration.
- `asyncio` — Although the function is async, `asyncio` is imported for potential future async utility.
- `ChatOpenAI` — LangChain's OpenAI-compatible chat model wrapper (used for both OpenAI and DeepSeek).
- `create_deep_agent` — The DeepAgents factory function that creates an autonomous agent with tool access.
- `FilesystemBackend` — The backend that provides filesystem tool implementations (read, write, glob, grep, etc.) to the agent.

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
   - `docs/api_reference.md` or component specific markdown files: Details on main classes, functions, and workflows.
5. Make sure the documentation is extremely detailed, readable, and polished. Do not leave placeholder text.
"""
```

A system prompt string that tells the LLM-powered agent:
- **Role**: expert technical writer and software architect.
- **Constraint**: Write all output inside the `docs/` folder.
- **Methodology**: Plan the audit using `write_todos`, then explore.
- **Tools**: Use `ls`, `read_file`, `glob`, `grep` to understand the codebase.
- **Outputs**: Generate three recommended files: `overview.md`, `architecture.md`, `api_reference.md`.
- **Quality**: Extremely detailed, readable, polished — no placeholder text.

### Functions

#### `run_doc_agent()`

Initializes and invokes the deep agent to audit a codebase and write documentation.

**Signature**:
```python
async def run_doc_agent(
    target_directory: str,
    specific_instructions: str = ""
) -> str
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_directory` | `str` | — | Absolute or relative path to the codebase root to document |
| `specific_instructions` | `str` | `""` | Optional custom guidance appended to the agent prompt |

**Returns**:
| Type | Description |
|------|-------------|
| `str` | The content of the final message from the agent (the agent's concluding response) |

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | When no API key is configured (propagated from `get_model()`) |
| Various | Any LangChain or DeepAgents exceptions during agent execution |

**Behavior**:
1. Prints `"🚀 Initializing Deep Documentation Agent for: {target_directory}"`.
2. Calls `get_model()` to obtain the appropriate LLM instance.
3. Creates a deep agent using `create_deep_agent()` with:
   - The selected LLM model.
   - A `FilesystemBackend` rooted at `target_directory` with `virtual_mode=False` (real filesystem access, not sandboxed virtual layer).
   - The `DOC_INSTRUCTIONS` system prompt.
4. Builds a user prompt that instructs the agent to audit the codebase at `target_directory` and write comprehensive markdown documentation.
5. Appends `specific_instructions` to the prompt if provided.
6. Invokes the agent via `agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})`.
7. Extracts the final message from the result dictionary: `result["messages"][-1].content`.
8. Returns the final message content as a string.

**Example**:
```python
result = await run_doc_agent("/home/user/project", "Highlight security concerns")
print(result)
```

**Internal workings**:
- The `agent.ainvoke()` call triggers the autonomous agent loop:
  1. LLM receives the system prompt (`DOC_INSTRUCTIONS`) and user prompt.
  2. LLM decides which tools to call (e.g., `write_todos` to plan, `ls` to explore, `read_file` to read source code).
  3. The FilesystemBackend executes the tool calls and returns results.
  4. LLM processes results and decides next action (more exploration, or writing documentation).
  5. The loop continues until the LLM determines the task is complete.
  6. The final LLM response is returned as the result.

---

#### `get_model()`

Selects and returns the appropriate LLM instance based on available API keys.

**Signature**:
```python
def get_model() -> Union[ChatOpenAI, ChatGoogleGenerativeAI]
```

**Returns**:
| Return Type | Condition |
|------------|-----------|
| `ChatGoogleGenerativeAI` | When `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set |
| `ChatOpenAI` | When `OPENAI_API_KEY` is set (and no Google key is present) |

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | When neither `OPENAI_API_KEY` nor `GOOGLE_API_KEY` / `GEMINI_API_KEY` is set |

**Behavior**:
1. Reads `OPENAI_API_KEY`, `GOOGLE_API_KEY`, and `GEMINI_API_KEY` from environment variables via `os.environ.get()`.
2. Strips leading/trailing whitespace from all found keys using `.strip()` (protects against accidental spaces in `.env`).
3. **Priority**: Google Gemini > OpenAI-compatible. If a Google key is present, it takes precedence.
4. **If Gemini is selected**:
   - Model name resolution: `MODEL_NAME` → `GOOGLE_MODEL_NAME` → `"gemini-1.5-flash"` (default).
   - Returns `ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key)`.
5. **If OpenAI-compatible is selected**:
   - Reads optional `OPENAI_BASE_URL` and strips whitespace.
   - Reads optional `MODEL_NAME`.
   - **DeepSeek auto-detection logic**:
     - Checks if the key starts with `"sk-"` and has exactly 32 hex characters after the prefix.
     - Detection code:
       ```python
       key_body = openai_key[3:] if openai_key.startswith("sk-") else openai_key
       is_deepseek_key = (len(key_body) == 32 and all(c in "0123456789abcdefABCDEF" for c in key_body))
       ```
     - If detected as DeepSeek:
       - Auto-sets `base_url` to `"https://api.deepseek.com"` (unless a non-OpenAI base URL is already explicitly set).
       - Auto-sets `model_name` to `"deepseek-chat"` (if not explicitly configured or still set to the default `"gpt-4o-mini"`).
   - Default model is `"gpt-4o-mini"` if nothing is configured.
   - Returns `ChatOpenAI(model=model_name, api_key=openai_key, base_url=base_url if base_url else None)`.

**DeepSeek Key Format**:
```
sk-5d63e78b553a431fbc7c618db5e3e1e0
#     ^--- exactly 32 hex characters after "sk-"
```

**Example `.env` configurations**:

```ini
# OpenAI
OPENAI_API_KEY=sk-proj-...standard_openai_format...
MODEL_NAME=gpt-4

# DeepSeek (auto-detected)
OPENAI_API_KEY=sk-5d63e78b553a431fbc7c618db5e3e1e0

# DeepSeek (explicit)
OPENAI_API_KEY=sk-5d63e78b553a431fbc7c618db5e3e1e0
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat

# Google Gemini
GOOGLE_API_KEY=AIzaSy...your_gemini_key...
MODEL_NAME=gemini-2.0-flash-exp

# Custom OpenAI-compatible endpoint
OPENAI_API_KEY=your-custom-key
OPENAI_BASE_URL=https://my-custom-llm-endpoint.com/v1
MODEL_NAME=custom-model
```

---

## Configuration Files

### `.env`

**Path**: `.env`

Environment variable configuration file. **Not committed to git** (listed in `.gitignore`).

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| `OPENAI_API_KEY` | `sk-...` | API key for OpenAI or DeepSeek |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Base URL override for compatible APIs |
| `GOOGLE_API_KEY` | `AIzaSy...` | API key for Google Gemini |
| `GEMINI_API_KEY` | `AIzaSy...` | Alias for `GOOGLE_API_KEY` |
| `MODEL_NAME` | `gpt-4o-mini` | Override the model name for the selected provider |
| `GOOGLE_MODEL_NAME` | `gemini-1.5-flash` | Gemini-specific model name override |

### `pyproject.toml`

**Path**: `pyproject.toml`

Project configuration file used by `uv` and `pip`.

#### Fields

| Field | Value |
|-------|-------|
| `name` | `"doc-agent"` |
| `version` | `"0.1.0"` |
| `description` | `"Add your description here"` |
| `readme` | `"README.md"` |
| `requires-python` | `">=3.13"` |

#### Dependencies

| Package | Version Constraint | Purpose |
|---------|-------------------|---------|
| `adapter` | `>=0.1` | Adapter pattern utilities for flexible integrations |
| `deepagents` | `>=0.6.2` | Agent orchestration framework with filesystem tool backends |
| `deepseek` | `>=1.0.0` | Official DeepSeek API client library |
| `langchain` | `>=1.3.1` | Core LLM abstraction framework (prompts, chains, calls) |
| `langchain-google-genai` | `>=4.2.2` | Google Gemini provider integration for LangChain |
| `langchain-mcp-adapters` | `>=0.2.2` | Adapters for Model Context Protocol (MCP) tool integration |
| `langchain-openai` | `>=1.2.1` | OpenAI-compatible provider integration for LangChain |
| `mcp` | `>=1.27.1` | Model Context Protocol SDK for standardized tool interfaces |

### `.python-version`

**Path**: `.python-version`

Contains `3.13` — used by `uv` and `pyenv` to pin the Python version for the virtual environment.

### `.gitignore`

**Path**: `.gitignore`

Excludes the following from version control:

```
# Python-generated files
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info

# Virtual environments
.venv
.env
```

---

## Module: `README.md`

**Path**: `README.md`

Currently a placeholder file (empty). Intended to be populated with project description, installation instructions, and usage examples. The Doc Agent's generated documentation inside `docs/` serves as the primary documentation for audited codebases.

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Documentation process completed successfully |
| `1` | Error occurred during agent execution (exception caught in `main()`) |

---

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

## Configuration: `.env`

**Path**: `/C:.env` (not tracked in git per `.gitignore`)

Example configuration:

```ini
OPENAI_API_KEY=sk-5d63e78b553a431fbc7c618db5e3e1e0
OPENAI_BASE_URL=https://api.openai.com/v1
```

Alternative Gemini configuration:

```ini
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL_NAME=gemini-1.5-flash
```

---

## Configuration: `.gitignore`

**Path**: `/.gitignore`

Ignores the following:

| Pattern | Reason |
|---------|--------|
| `__pycache__/` | Compiled Python bytecode |
| `*.py[oc]` | Compiled Python files |
| `build/`, `dist/`, `wheels/` | Build artifacts |
| `*.egg-info` | Package metadata |
| `.venv` | Virtual environment |
| `.env` | API keys and secrets |

---

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
        virtual_mode=False
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
FilesystemBackend(root_dir="/path", virtual_mode=False)
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
