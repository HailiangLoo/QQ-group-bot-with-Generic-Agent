# Memory Design

The memory system has three layers.

## 1. Live Memory

Live memory stores the messages the small account can currently see.

Use it for:

- recent 50-100 messages;
- current reply context;
- follow-up judgement;
- incremental learning batches.

Do not send the whole live database into every model call.

## 2. Image Caption Cache

Each image is hashed by bytes. If the same image appears again, reuse the stored caption.

Recommended cache key:

```text
sha256(image_bytes) + hash(caption_instruction)
```

This lets you store:

- a general caption;
- a meme-focused caption;
- an OCR-focused caption;
- a UI/screenshot-focused caption.

The first caption can be a few hundred Chinese characters. Let the vision model decide how much detail is needed, but set a generous output limit so complex screenshots are not truncated.

## 3. Deep Profiles and Episodes

Deep profiles are not chat logs. They are retrieval-ready notes:

- member interests and recurring topics;
- communication preferences;
- relationship dynamics;
- important events;
- corrections the user gave the agent;
- naming preferences;
- sensitive boundaries;
- "do not call me X, call me Y" style instructions;
- stable running jokes.

Episodes are event records. They should preserve who, when, what happened, why it matters, and confidence.

Example:

```json
{
  "id": "ep_2026_04_25_001",
  "time_hint": "2026-04-25 morning",
  "participants": ["member_a", "agent"],
  "type": "preference",
  "summary": "member_a corrected the agent's wording preference.",
  "evidence": ["short quoted snippet"],
  "memory_update": "Use the preferred name in future replies.",
  "confidence": "high"
}
```

## Incremental Learning

A practical schedule:

- every 100-300 new visible messages, create a small learning batch;
- extract new preferences, recurring topics, corrections, and unresolved questions;
- update shallow indexes quickly;
- run deeper profile updates less often, using a stronger model.

The agent should learn from corrections with high priority. Corrections are often more valuable than ordinary chat.

