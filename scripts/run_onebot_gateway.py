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
from group_memory_agent.runner import StubAgentRunner


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    config = load_config(args.config)
    memory = LiveMemory(config.memory.db_path)
    gateway = OneBotGateway(config, memory, StubAgentRunner())
    print(f"[gateway] connecting to {config.onebot.ws_url}")
    print("[gateway] using StubAgentRunner; wire a real runner before production")
    await gateway.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

