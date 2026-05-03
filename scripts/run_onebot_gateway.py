from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from group_memory_agent.config import load_config
from group_memory_agent.live_memory import LiveMemory
from group_memory_agent.onebot_gateway import OneBotGateway
from group_memory_agent.runner import OpenAICompatibleRunner, StubAgentRunner


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.toml")
    parser.add_argument(
        "--runner",
        choices=["stub", "openai"],
        default="stub",
        help="Use stub for transport tests or openai for an OpenAI-compatible text model.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    memory = LiveMemory(config.memory.db_path)
    runner = OpenAICompatibleRunner(config.text_model) if args.runner == "openai" else StubAgentRunner()
    gateway = OneBotGateway(config, memory, runner)
    print(f"[gateway] connecting to {config.onebot.ws_url}")
    print(f"[gateway] runner={args.runner}")
    if args.runner == "stub":
        print("[gateway] using StubAgentRunner; use --runner openai or wire GenericAgent before production")
    await gateway.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
