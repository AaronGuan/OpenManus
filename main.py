import argparse
import asyncio
import os
import sys

from app.agent.manus import Manus
from app.logger import logger


async def main():
    # Make stdout/stderr more robust on Windows terminals (e.g. GBK cp936).
    # Prevent UnicodeEncodeError when model outputs emojis or non-GBK chars.
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
            except Exception:
                pass

    def safe_print(text: str) -> None:
        if not text:
            return
        try:
            print(text)
        except UnicodeEncodeError:
            # Fallback: write via the original stdout with replacement.
            out = getattr(sys, "__stdout__", sys.stdout)
            try:
                out.write(text.encode("utf-8", errors="replace").decode("utf-8") + "\n")
            except Exception:
                # Last resort: drop unencodable chars
                out.write((text + "\n").encode(errors="replace").decode(errors="replace"))

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the agent"
    )
    args = parser.parse_args()

    # Create and initialize Manus agent
    agent = await Manus.create()
    try:
        def _last_assistant_text() -> str:
            for msg in reversed(agent.memory.messages):
                if getattr(msg, "role", None) == "assistant" and getattr(msg, "content", None):
                    return msg.content
            return ""

        # If prompt is provided, run once and exit.
        if args.prompt is not None:
            prompt = args.prompt
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
                return
            logger.warning("Processing your request...")
            await agent.run(prompt, cleanup=False)
            reply = _last_assistant_text()
            if reply:
                safe_print(reply)
            logger.info("Request processing completed.")
            return

        # Interactive multi-turn chat loop (same agent, preserves context).
        while True:
            prompt = input("Enter your prompt (type 'exit' to quit): ").strip()
            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit"}:
                break

        logger.warning("Processing your request...")
            await agent.run(prompt, cleanup=False)
            reply = _last_assistant_text()
            if reply:
                safe_print(reply)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
