import argparse
import asyncio
import sys
from dotenv import load_dotenv
from agent import run_doc_agent

# Support UTF-8 emoji and markdown outputs in Windows/CMD standard terminal
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file (optional — users can also pass flags)
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        prog="doc-agent",
        description=(
            "doc-agent: AI-powered CLI tool that automatically generates markdown documentation\n"
            "for any codebase using an LLM agent.\n\n"
            "Supported providers: OpenAI, Google Gemini, DeepSeek (auto-detected from key format)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Path to the codebase directory to document (default: current directory '.')"
    )
    parser.add_argument(
        "--instructions", "-i",
        default="",
        help="Custom guidance for the agent (e.g. 'Focus on API endpoints only')"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help=(
            "Your LLM API key. Accepts OpenAI, Google Gemini, or DeepSeek keys. "
            "If not provided, falls back to OPENAI_API_KEY / GOOGLE_API_KEY in your environment or .env file."
        )
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help=(
            "Model name to use (e.g. 'gpt-4o', 'gemini-1.5-pro', 'deepseek-chat'). "
            "Auto-selected based on your API key if not specified."
        )
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Custom OpenAI-compatible API base URL (e.g. 'https://api.deepseek.com'). "
            "Only needed for non-OpenAI providers using the OpenAI SDK format."
        )
    )

    args = parser.parse_args()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("       📄  DOCUMENTATION WRITER        ")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📁 Target Directory : {args.directory}")
    if args.instructions:
        print(f"📝 Instructions     : {args.instructions}")
    if args.model:
        print(f"🤖 Model Override   : {args.model}")
    if args.base_url:
        print(f"🔗 Base URL         : {args.base_url}")
    print()

    try:
        result = asyncio.run(
            run_doc_agent(
                args.directory,
                args.instructions,
                api_key=args.api_key,
                model_name=args.model,
                base_url=args.base_url,
            )
        )
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  ✅  Documentation generated successfully!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        print(result)
    except Exception as e:
        print(f"\n❌ Error running documentation agent: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
