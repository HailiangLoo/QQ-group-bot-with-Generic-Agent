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
  |-- treats QQ file segments that are actually images as images
  |-- resolves quoted-message anchors when available
  |-- decides whether the persona should reply
  |-- builds a compact context pack
  |-- records self-improvement events for later human review
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
- redact raw OneBot payloads unless explicitly enabled;
- write live messages into SQLite;
- dedupe and cache image captions;
- keep quoted-message context reachable without exposing the whole database;
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
5. If replying, it builds a context pack. If the current message quotes an older message outside the normal context window, a bounded anchor window is added.
6. The main runner answers. If it outputs `[NO_REPLY]`, nothing is sent.
7. The reply is sent through OneBot, preferably as a native quote instead of hand-written `@someone`.
8. Errors, no-reply decisions, failed captions, duplicate replies, and other learnable failures can be appended to a proposal-only self-improvement queue.
9. Follow-up listening is armed for a short window after the persona speaks.

## Prompt Engineering First

The runtime should not create a small classifier for every possible behavior. Prefer putting stable behavior policy in the main reply prompt when it can be expressed as normal conversation judgement:

- current message has priority over previous completed tasks;
- recommendations should be useful and structured instead of only a meme reply;
- images are evidence from the vision module, not a reason for the main model to inspect files;
- follow-up/auto routes may output `[NO_REPLY]` if the message is really for another person.

Use extra model calls only when they materially reduce cost or prevent noisy replies, such as image captioning, follow-up probability sampling, or explicit tool gating.
