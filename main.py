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

# Load environment variables from .env file
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="CLI Documentation Writer - Automate generating beautiful markdown docs for your codebases."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="The path to the codebase directory to document (defaults to current directory '.')"
    )
    parser.add_argument(
        "--instructions",
        "-i",
        default="",
        help="Specific guidance or instructions for the agent (e.g., 'Focus on API endpoints')"
    )
    
    args = parser.parse_args()
    

    print("         DOCUMENTATION WRITER             ")

    print(f"Target Directory: {args.directory}")
    if args.instructions:
        print(f"Custom Instructions: {args.instructions}")

    
    try:
        # run_doc_agent is async, so we run it using asyncio
        result = asyncio.run(run_doc_agent(args.directory, args.instructions))
        print("\n====================================================")
        print("🎉 Documentation Process Completed successfully!")
        print("====================================================")
        print(result)
    except Exception as e:
        print(f"\n❌ Error running documentation agent: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
