import os
import asyncio
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

DOC_INSTRUCTIONS = """You are an expert technical writer and software architect.
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

async def run_doc_agent(target_directory: str, specific_instructions: str = ""):
    """
    Initializes and invokes the deep agent to audit a codebase and write markdown documentation.
    """
    # Resolve absolute path of the target directory to ensure robust backend scoping
    abs_target_dir = os.path.abspath(target_directory)
    print(f"🚀 Initializing Deep Documentation Agent for target: {abs_target_dir}")
    
    model = get_model()

    agent = create_deep_agent(
        model,
        backend=FilesystemBackend(root_dir=abs_target_dir, virtual_mode=False),
        system_prompt=DOC_INSTRUCTIONS,
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

def get_model():
    openai_key = os.environ.get("OPENAI_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    # Strip whitespace if set in .env with leading spaces
    if openai_key:
        openai_key = openai_key.strip()
    if google_key:
        google_key = google_key.strip()
        
    if google_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = os.environ.get("MODEL_NAME") or os.environ.get("GOOGLE_MODEL_NAME") or "gemini-1.5-flash"
        print(f"🤖 Using Gemini Model: {model_name}")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_key,
        )
    elif openai_key:
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url:
            base_url = base_url.strip()
            
        model_name = os.environ.get("MODEL_NAME")
        
        # Auto-detect if key is DeepSeek (starts with sk- followed by 32 hex digits)
        is_deepseek_key = False
        key_body = openai_key[3:] if openai_key.startswith("sk-") else openai_key
        if len(key_body) == 32 and all(c in "0123456789abcdefABCDEF" for c in key_body):
            is_deepseek_key = True
            
        if is_deepseek_key:
            # If standard OpenAI url is set but the key is a DeepSeek key, self-heal and point to DeepSeek
            if not base_url or "openai.com" in base_url:
                print("🔄 Auto-detected DeepSeek key format! Auto-redirecting Base URL to: https://api.deepseek.com")
                base_url = "https://api.deepseek.com"
            if not model_name or model_name == "gpt-4o-mini":
                print("🔄 Auto-detected DeepSeek key format! Auto-setting Model to: deepseek-chat")
                model_name = "deepseek-v4-flash"
        
        if not model_name:
            model_name = "gpt-4o-mini"
            
        print(f"🤖 Using OpenAI-compatible Model: {model_name} (Base URL: {base_url or 'default'})")
        return ChatOpenAI(
            model=model_name,
            api_key=openai_key,
            base_url=base_url if base_url else None,
        )
    else:
        raise ValueError(
            "No API Key found! Please set GOOGLE_API_KEY or OPENAI_API_KEY in your .env file."
        )
