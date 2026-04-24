# QCE, WSL, OneBot, and GenericAgent

The clean deployment has four layers:

```text
Windows
  QQ small account
  QCE / NapCat
  OneBot WebSocket server

WSL or Windows
  group-memory-agent gateway

WSL
  GenericAgent
  memory/index
  group_memory/live
```

## Recommended Layout

For the lowest-friction setup, keep QQ and QCE/NapCat on Windows, because the graphical QQ client already runs there. Run the gateway either on Windows or in WSL.

If the gateway runs in WSL, `127.0.0.1` inside WSL may refer to WSL itself, not Windows. Use one of these:

- configure QCE/NapCat to listen on an address WSL can reach;
- use the Windows host address from WSL;
- run the gateway on Windows and call GenericAgent through WSL commands.

## OneBot Boundary

OneBot is the transport API. The gateway expects group message events like:

```json
{
  "post_type": "message",
  "message_type": "group",
  "group_id": 123,
  "user_id": 456,
  "raw_message": "hello",
  "message": [
    {"type": "text", "data": {"text": "hello"}}
  ]
}
```

To send a reply, the gateway emits:

```json
{
  "action": "send_group_msg",
  "params": {
    "group_id": 123,
    "message": "reply text"
  }
}
```

## GenericAgent Boundary

GenericAgent should be treated as the final reasoning and persona engine. The gateway should not leak transport details into the agent. Pass a context pack instead:

```text
system/persona rules
recent messages
image captions
retrieved memory snippets
current message
reply reason
```

The gateway's `AgentRunner` interface is deliberately small so you can plug in:

- a subprocess call to GenericAgent;
- an OpenAI-compatible chat completion request;
- a local debug stub.

## Keep These Separate

- QCE/NapCat: receives and sends QQ messages.
- Gateway: routing, memory, context building, image cache.
- GenericAgent: final thinking and persona reply.
- Deep profile distillation: offline or scheduled learning, not required for every message.

