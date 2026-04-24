# Group Memory Agent

Group Memory Agent is a clean, open-sourceable skeleton for a QQ group chat persona agent.
It separates the reusable architecture from private data: no real chat logs, API keys, QQ ids,
member profiles, or inside jokes are included.

Chinese maintainer notes: [README.zh-CN.md](README.zh-CN.md)

The intended private deployment looks like this:

```text
Windows QQ small account
  |
  | QCE / NapCat
  v
OneBot WebSocket
  |
  v
group-memory-agent gateway
  |-- live SQLite memory
  |-- image caption cache
  |-- follow-up trigger classifier
  |-- auto reply policy
  v
GenericAgent or another LLM runner
  |
  v
OneBot send_group_msg
```

## What This Project Provides

- OneBot/QCE/NapCat integration boundary.
- Live message storage in SQLite.
- Image caption caching by content hash.
- A stable final-speaker design: use a cheap/fast vision model only to describe images, then let the main text model keep the persona.
- Trigger policy:
  - explicit trigger words;
  - follow-up listening after the agent speaks;
  - idle new-topic reply;
  - long-message summary;
  - low-frequency keyword/random banter.
- Prompt templates for context packs and group-style replies.
- Documentation for how QCE, WSL, OneBot, GenericAgent, and model routing fit together.

## What Is Intentionally Not Included

- Real QQ chat exports.
- Member profiles, relationship summaries, episodes, or live memory from any real group.
- API keys.
- QQ account credentials, group ids, user ids, openids, nicknames, or aliases.
- Private prompts that expose a real group's social structure.

## Quick Start

1. Install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

2. Copy the example config:

```bash
cp examples/config.example.toml config.toml
```

3. Start QCE/NapCat and make sure OneBot WebSocket is listening, usually:

```text
ws://127.0.0.1:3001
```

4. Run the gateway:

```bash
python scripts/run_onebot_gateway.py --config config.toml
```

The default runner in this clean skeleton is a stub. Wire `AgentRunner.reply()` to GenericAgent,
OpenAI-compatible chat completions, or your own agent loop.

## Core Rule

Historical group chat is data, not instruction. The agent should use memory as context, but must not
publicly expose complete private profiles or raw chat logs.

## Docs

- [Architecture](docs/architecture.md)
- [QCE, WSL, OneBot, and GenericAgent](docs/qce-wsl-genericagent.md)
- [Trigger Policy](docs/trigger-policy.md)
- [Memory Design](docs/memory-design.md)
- [Operations](docs/operations.md)
- [Privacy and Open Source Hygiene](docs/privacy.md)
