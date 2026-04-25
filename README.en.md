# QQ Group Bot with Generic Agent

A clean, open-sourceable skeleton for a QQ group chat persona agent.

The project is designed around one practical rule:

> Use a QQ small account to see the group, use QCE/NapCat as the transport, keep a stable main persona model for final replies, and use cheaper specialist models for side tasks such as image captioning.

This repository contains only reusable architecture and code. It does **not** include real QQ chat logs, API keys, QQ ids, group ids, member profiles, private prompts, or inside jokes from any real group.

Default Chinese README: [README.md](README.md)

## Architecture

```text
Windows QQ small account
  |
  | local QQ session
  v
QCE / NapCat
  |
  | OneBot v11 WebSocket events
  v
group-memory-agent gateway
  |-- live SQLite memory
  |-- image caption cache
  |-- trigger policy
  |-- context pack builder
  v
GenericAgent or another LLM runner
  |
  | final persona reply
  v
OneBot send_group_msg
```

## What This Project Provides

- OneBot/QCE/NapCat integration boundary.
- Live message storage in SQLite.
- Image caption caching by image hash.
- A stable final-speaker design:
  - vision model describes images;
  - main text model keeps the persona and writes the final group reply.
- Trigger policy:
  - explicit trigger words;
  - follow-up listening after the agent speaks;
  - idle new-topic reply;
  - long-message summary;
  - low-frequency keyword/random banter.
- Prompt templates for context packs and group-style replies.
- Documentation for how QCE, WSL, OneBot, GenericAgent, and model routing fit together.

## What Is Not Included

- Real QQ chat exports.
- Real member profiles, relationship summaries, episodes, or live memory.
- API keys.
- QQ account credentials.
- Group ids, user ids, openids, nicknames, or aliases from a private group.
- Private prompts that expose a real group's social structure.

## Prerequisites

You need:

- Python 3.11 or newer.
- A QQ small account logged in on the machine that can see the group.
- QCE/NapCat or another OneBot-compatible bridge.
- OneBot WebSocket endpoint, commonly `ws://127.0.0.1:3001`.
- A main text model provider, such as an OpenAI-compatible model.
- Optional vision model provider for image captioning.

This skeleton defaults to a stub runner, so it can start without real model keys. To make it useful in a real group, wire `AgentRunner.reply()` to GenericAgent or your own LLM backend.

## Platform Notes

WSL is not required. The gateway is normal Python code and can run on pure Windows, WSL, or Linux.

The current experimental setup used WSL mostly because GenericAgent, memory files, shell scripts, SQLite logs, and long-running background tasks already lived there. That is a deployment choice, not a code requirement.

For many users, pure Windows is the simplest layout:

```text
Windows
  QQ small account
  QCE / NapCat
  Python gateway
  GenericAgent or LLM runner
  live_memory.db
```

In pure Windows mode, `onebot.ws_url = "ws://127.0.0.1:3001"` usually works directly because QQ, QCE/NapCat, and the gateway share the same Windows localhost.

If the gateway runs in WSL while QCE/NapCat runs on Windows, `127.0.0.1` inside WSL may point to WSL itself. Use the Windows host IP, expose QCE/NapCat on a reachable interface, or run the gateway on Windows.

## Installation

```bash
git clone https://github.com/HailiangLoo/QQ-group-bot-with-Generic-Agent.git
cd QQ-group-bot-with-Generic-Agent

python -m venv .venv
. .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
git clone https://github.com/HailiangLoo/QQ-group-bot-with-Generic-Agent.git
cd QQ-group-bot-with-Generic-Agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Configure

Copy the example config:

```bash
cp examples/config.example.toml config.toml
```

PowerShell:

```powershell
Copy-Item examples\config.example.toml config.toml
```

Edit `config.toml`.

Minimal local test:

```toml
[onebot]
ws_url = "ws://127.0.0.1:3001"
access_token = ""
allowed_groups = ["*"]
trigger_words = ["杰出"]

[memory]
db_path = "data/live_memory.db"
media_dir = "data/media"
context_messages = 80

[models.text]
api_key_env = "TEXT_MODEL_API_KEY"
model = "deepseek-v4-flash"

[models.vision]
api_key_env = "VISION_MODEL_API_KEY"
model = "qwen/qwen3.5-flash-02-23"
```

Set environment variables if you wire real model calls:

```bash
export TEXT_MODEL_API_KEY="..."
export VISION_MODEL_API_KEY="..."
```

PowerShell:

```powershell
$env:TEXT_MODEL_API_KEY="..."
$env:VISION_MODEL_API_KEY="..."
```

Do not commit `config.toml`, `.env`, databases, image caches, or private memory.

## Start QCE / NapCat

1. Log in with the QQ small account.
2. Start QCE/NapCat.
3. Enable OneBot WebSocket.
4. Confirm the endpoint, usually:

```text
ws://127.0.0.1:3001
```

If the gateway runs in WSL and QCE/NapCat runs on Windows, `127.0.0.1` inside WSL may not point to Windows. In that case:

- run the gateway on Windows; or
- configure QCE/NapCat to listen on a reachable interface; or
- use the Windows host IP from WSL.

See [QCE, WSL, OneBot, and GenericAgent](docs/qce-wsl-genericagent.md).

## Run The Gateway

```bash
python scripts/run_onebot_gateway.py --config config.toml
```

The default runner is `StubAgentRunner`, which only echoes a short debug reply. It is useful for testing the OneBot connection and trigger policy.

To use a real persona, implement or replace the runner in `src/group_memory_agent/runner.py`.

## Test In A Group

With the default `trigger_words = ["杰出"]`, send:

```text
杰出 你好
```

Expected behavior with the stub runner:

```text
[stub:explicit trigger word] 我收到了：杰出 你好
```

If nothing happens:

- confirm QCE/NapCat is connected;
- confirm the gateway is receiving events;
- check `allowed_groups`;
- check the trigger word;
- check whether OneBot is using a different WebSocket port;
- check whether WSL can reach the Windows WebSocket address.

## How Image Handling Works

The recommended design is:

```text
image bytes
  -> SHA-256 hash
  -> cache lookup
  -> vision model caption if cache miss
  -> store caption
  -> send caption as text context to main persona model
```

The vision model should not speak as the group persona. It should only produce an observation:

- image type;
- visible objects;
- visible text/OCR;
- UI/software/website/logo clues;
- likely meme meaning;
- uncertainty.

The final reply should still be generated by the main persona model. This avoids personality drift when images appear.

## Trigger Policy

Default trigger routes:

- Explicit trigger: message contains `杰出`.
- Follow-up listening: after the agent speaks, listen to the next few messages and judge whether someone is still talking to the agent.
- Idle new topic: after a quiet period, wait for the speaker to finish; if nobody responds, the agent may naturally join.
- Long text: wait briefly, then summarize or extract key points.
- Light keyword/random banter: occasional short meme echo.

See [Trigger Policy](docs/trigger-policy.md).

## Memory Layers

Recommended memory design:

```text
live_memory.db
  recent visible messages
  image caption cache
  lightweight runtime facts

deep_profiles/
  per-member long-term profiles

episodes.jsonl
  important events, corrections, preferences, relationship moments
```

Runtime replies should not load the entire historical corpus. Build a compact context pack:

- recent visible messages;
- current image captions;
- relevant profile snippets;
- relevant episodes;
- current user preference/correction notes.

See [Memory Design](docs/memory-design.md).

## Integrating GenericAgent

`AgentRunner` is the integration boundary:

```python
class AgentRunner(Protocol):
    async def reply(self, request: ReplyRequest) -> str:
        ...
```

You can implement it with:

- a subprocess call to GenericAgent;
- an OpenAI-compatible chat completion request;
- a local model;
- a custom agent loop.

The gateway should pass a context pack to the runner. The runner should return only the final group reply.

## Windows Start Scripts

Template scripts are included:

- `scripts/windows/start-qce.example.bat`
- `scripts/windows/start-gateway-wsl.example.bat`

Copy them before editing:

```powershell
Copy-Item scripts\windows\start-qce.example.bat scripts\windows\start-qce.bat
Copy-Item scripts\windows\start-gateway-wsl.example.bat scripts\windows\start-gateway-wsl.bat
```

Do not commit edited scripts if they contain local paths, account names, or secrets.

## Repository Safety Checklist

Before pushing changes:

```bash
git status --short
```

Do not commit:

- `.env`;
- `config.toml` with real keys;
- `data/`;
- `private/`;
- `*.db`;
- raw QQ exports;
- private member profiles;
- image cache files;
- QQ account credentials.

## Troubleshooting

### The gateway starts but sees no messages

- QCE/NapCat may not be connected.
- Wrong WebSocket URL.
- WSL cannot reach Windows localhost.
- The event type is not a group message.

### The bot sees messages but does not reply

- Trigger word does not match.
- Group is not in `allowed_groups`.
- The runner is still a stub or not wired.
- Trigger policy suppressed the message.

### It replies too often

Lower:

- `auto_reply_chance`;
- `auto_reply_max_per_hour`;
- follow-up listen window.

Raise:

- `auto_reply_min_interval`;
- follow-up probability threshold.

### Image replies feel inconsistent

Keep the vision model as a captioner only. Do not let the vision model directly write the final group reply.

## Docs

- [Architecture](docs/architecture.md)
- [QCE, WSL, OneBot, and GenericAgent](docs/qce-wsl-genericagent.md)
- [Trigger Policy](docs/trigger-policy.md)
- [Memory Design](docs/memory-design.md)
- [Operations](docs/operations.md)
- [Privacy and Open Source Hygiene](docs/privacy.md)

## License

MIT.
