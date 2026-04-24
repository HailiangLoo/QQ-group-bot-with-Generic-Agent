# Architecture

This project splits a group persona agent into small, replaceable parts.

```text
QQ small account
  |
  | local QQ client session
  v
QCE / NapCat sidecar
  |
  | OneBot v11 WebSocket events
  v
group-memory-agent
  |-- stores visible group messages
  |-- captions images once and caches the result
  |-- decides whether the persona should reply
  |-- builds a compact context pack
  v
GenericAgent / LLM runner
  |
  | final persona reply
  v
OneBot send_group_msg
```

## Responsibilities

### QQ Small Account

The small account is the group member that can see normal group messages. It is not the same thing as an official QQ bot account.

Use it only in groups where this is acceptable. The account should behave like a normal participant: low message rate, no spam, no mass unsolicited messages.

### QCE / NapCat

QCE/NapCat is the bridge between the local QQ session and the agent. It exposes OneBot-compatible events such as group messages and image attachments.

It should not contain persona logic. Treat it as transport only.

### group-memory-agent

This gateway owns the reusable behavior:

- parse OneBot events;
- write live messages into SQLite;
- dedupe and cache image captions;
- decide explicit, follow-up, idle, long-text, and light banter triggers;
- build context packs;
- call the final text/persona runner;
- send the final reply back through OneBot.

### Vision Model

The vision model is not the persona. It should only turn images into high-quality observations:

```text
image -> structured caption / visible text / likely UI / possible joke
```

The final response still goes through the main persona model. This keeps personality stable and avoids switching voice every time an image appears.

### GenericAgent / Main Runner

The main runner is the stable "speaker". It receives:

- recent live context;
- image captions;
- retrieved profiles / memories;
- the user's current message;
- trigger reason.

Then it produces the final group-style reply.

## Data Flow

1. A group message arrives from OneBot.
2. The gateway stores raw visible text and metadata.
3. If the message has an image:
   - hash the image bytes;
   - reuse a cached caption if available;
   - otherwise call the vision model once and store the caption.
4. The gateway decides whether to reply.
5. If replying, it builds a context pack and calls the main runner.
6. The reply is sent through OneBot.
7. Follow-up listening is armed for a short window after the persona speaks.

