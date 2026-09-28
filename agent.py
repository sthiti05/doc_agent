import os
import asyncio
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import FilesystemBackend

DOC_INSTRUCTIONS = """You are an expert technical writer and software architect.
Your mission is to audit the provided codebase, understand its layout, core modules, architecture, and functions, and write high-quality markdown documentation.

CRITICAL DIRECTIVES:
1. ALWAYS write all generated documentation files inside the `docs/` folder (relative to your workspace root). If the `docs/` folder does not exist, create it using your file tools. Do not write any documents outside the `docs/` folder.
2. First, use 'write_todos' to plan which modules, directories, and files you need to audit.
3. Read the entry points and code structure (using 'ls', 'read_file', 'glob', etc.) to understand functional dependencies.
4. Create clear, concise, and structured documentation files. Recommended files to write inside the `docs/` folder:
   - `docs/overview.md`: Summary of the project, features, and folder structure.Conceptual explanation of design, modules, and how they interact.
5. Do not leave placeholder text.
6. NEVER read, open, or reference the `.env` or `.gitignore` files. These files contain sensitive configuration and must be completely ignored.
"""

async def run_doc_agent(
    target_directory: str,
    specific_instructions: str = "",
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
):
    """
    Initializes and invokes the deep agent to audit a codebase and write markdown documentation.

    Args:
        target_directory: Path to the codebase directory to document.
        specific_instructions: Optional extra guidance for the agent.
        api_key: LLM API key (OpenAI, Gemini, or DeepSeek). Falls back to env vars if not provided.
        model_name: Override the model to use (e.g. 'gpt-4o', 'gemini-1.5-pro').
        base_url: Custom OpenAI-compatible base URL for non-OpenAI providers.
    """
    # Resolve absolute path of the target directory to ensure robust backend scoping
    abs_target_dir = os.path.abspath(target_directory)
    print(f"🚀 Initializing Deep Documentation Agent for target: {abs_target_dir}")

    model = get_model(api_key=api_key, model_name=model_name, base_url=base_url)

    # Deny the agent from reading sensitive/config files.
    # Include multiple path formats to cover all possible matching strategies
    # used by the deepagents FilesystemBackend (absolute-style, relative, and glob).
    denied_files = FilesystemPermission(
        operations=["read"],
        paths=[
            "/.env",        # root .env
            "/**/.env",     # any nested .env in subdirectories
            "/.gitignore",  # root .gitignore
            "/**/.gitignore", # any nested .gitignore in subdirectories
        ],
        mode="deny",
    )

    agent = create_deep_agent(
        model,
        backend=FilesystemBackend(root_dir=abs_target_dir, virtual_mode=True),
        system_prompt=DOC_INSTRUCTIONS,
        permissions=[denied_files],
    )
    
    prompt = (
        "Please audit the codebase located in your current workspace directory ('.'). "
        "Analyze its contents, files, and modules, and write comprehensive markdown documentation for it. "
        "Remember, you MUST save all documentation files inside the `docs/` folder (creating it if it doesn't exist)."
    )
    if specific_instructions:
        prompt += f" Additional guidance: {specific_instructions}"
    
    print("🚦 Starting documentation run. Analyzing codebase...", flush=True)
    final_answer = ""
    
    async for event in agent.astream({
        "messages": [{"role": "user", "content": prompt}]
    }):
        for node_name, node_val in event.items():
            if isinstance(node_val, dict) and "messages" in node_val:
                messages = node_val["messages"]
                if not messages:
                    continue
                last_msg = messages[-1]
                
                if node_name == "tools":
                    # Tool execution output
                    tool_name = getattr(last_msg, "name", "unknown")
                    content = last_msg.content
                    summary = str(content).strip().replace("\r", "").replace("\n", " ")
                    if len(summary) > 120:
                        summary = summary[:117] + "..."
                    print(f"   └─ 💻 Tool [{tool_name}] output: {summary}", flush=True)
                
                elif node_name == "model":
                    # Model response / thought
                    if last_msg.content:
                        content = last_msg.content.strip()
                        if content:
                            print(f"\n🧠 Agent response:\n{content}\n", flush=True)
                            final_answer = last_msg.content
                    
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            tool_name = tc.get("name", "")
                            tool_args = tc.get("args", {})
                            print(f"🔍 Agent decided to run tool [{tool_name}]", flush=True)
                            print(f"   ├─ Arguments: {tool_args}", flush=True)
    
    return final_answer

def get_model(
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
):
    """
    Resolves and returns the appropriate LangChain chat model.

    Priority for each value: CLI flag > environment variable > auto-detected default.
    Supports OpenAI, Google Gemini, and DeepSeek (auto-detected from key format).
    """
    # --- Resolve keys: CLI flag takes priority over environment variables ---
    openai_key = api_key or os.environ.get("OPENAI_API_KEY")
    google_key = None
    if not api_key:
        # Only fall back to Google env vars if no explicit key was provided via CLI
        google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    # Strip accidental whitespace from keys loaded via .env
    if openai_key:
        openai_key = openai_key.strip()
    if google_key:
        google_key = google_key.strip()

    # --- Resolve base URL: CLI flag > env var ---
    if not base_url:
        base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        base_url = base_url.strip()

    # --- Resolve model name: CLI flag > env var ---
    if not model_name:
        model_name = os.environ.get("MODEL_NAME")

    # --- Azure OpenAI path ---
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if azure_key:
        from langchain_openai import ChatOpenAI
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
        
        # Azure Model-as-a-Service (MaaS) endpoints running 3rd party models expect
        # the standard OpenAI JSON body (including the "model" field), but are routed
        # through the Azure deployment URL path. We use ChatOpenAI to preserve the body,
        # but construct the Azure-specific base URL and inject the api-version query param.
        base_url = f"{endpoint}/openai/deployments/{deployment}"
        
        print(f"🤖 Using Azure AI Serverless Model: {deployment}")
        return ChatOpenAI(
            model=deployment,
            api_key=azure_key.strip(),
            base_url=base_url,
            default_query={"api-version": api_version},
            default_headers={"api-key": azure_key.strip()}
        )

    # --- Google Gemini path ---
    if google_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        resolved_model = model_name or os.environ.get("GOOGLE_MODEL_NAME") or "gemini-1.5-flash"
        print(f"🤖 Using Gemini Model: {resolved_model}")
        return ChatGoogleGenerativeAI(
            model=resolved_model,
            google_api_key=google_key,
        )

    # --- OpenAI / DeepSeek path ---
    elif openai_key:
        # Auto-detect DeepSeek key format (sk- followed by exactly 32 hex characters)
        key_body = openai_key[3:] if openai_key.startswith("sk-") else openai_key
        is_deepseek_key = len(key_body) == 32 and all(c in "0123456789abcdefABCDEF" for c in key_body)

        if is_deepseek_key:
            if not base_url or "openai.com" in base_url:
                print("🔄 Auto-detected DeepSeek key! Redirecting Base URL to: https://api.deepseek.com")
                base_url = "https://api.deepseek.com"
            if not model_name or model_name == "gpt-4o-mini":
                print("🔄 Auto-detected DeepSeek key! Setting model to: deepseek-chat")
                model_name = "deepseek-chat"

        resolved_model = model_name or "gpt-4o-mini"
        print(f"🤖 Using OpenAI-compatible Model: {resolved_model} (Base URL: {base_url or 'default openai'})")
        return ChatOpenAI(
            model=resolved_model,
            api_key=openai_key,
            base_url=base_url if base_url else None,
        )

    else:
        raise ValueError(
            "No API key found!\n\n"
            "Please provide your key using one of these methods:\n"
            "  1. CLI flag:        doc-agent ./my-project --api-key YOUR_KEY\n"
            "  2. Environment var: set OPENAI_API_KEY=YOUR_KEY  (or GOOGLE_API_KEY)\n"
            "  3. .env file:       create a .env file with OPENAI_API_KEY=YOUR_KEY\n"
        )
