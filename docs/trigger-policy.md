# Trigger Policy

The persona should feel present without becoming noisy. The default policy uses several routes.

## 1. Explicit Trigger

If a message contains a trigger word such as `杰出`, reply directly.

This bypasses the follow-up classifier.

## 2. Follow-Up Listening

After the persona replies, it listens to the next few non-agent messages.

Default:

- listen to next 6 messages;
- expire after 10 minutes;
- judge only recent short context;
- reply only when the probability is high.

The follow-up judge should output JSON:

```json
{
  "p": 0.81,
  "should_reply": true,
  "reason": "The user is correcting the agent's last answer."
}
```

Suggested thresholds:

- `p >= 0.72`: reply;
- `0.45 <= p < 0.72`: wait a few seconds and cancel if newer messages arrive;
- `< 0.45`: ignore.

## 3. Idle New Topic

If the group has been quiet for about 15 minutes and one person starts talking, the agent may wait for that person to finish.

Default:

- idle gap: 15 minutes;
- after the speaker's last message, wait 120 seconds;
- if nobody else replies, the persona may naturally answer.

If the same speaker keeps sending messages, refresh the wait timer. Do not interrupt them mid-thought.

## 4. Long Text

If someone posts a long message, the agent can offer a summary or extract the point.

Default:

- visible text length over 300 characters;
- wait 45 seconds;
- if the same speaker continues, refresh;
- if another person replies, cancel.

## 5. Light Keyword / Random Banter

For low-stakes group presence, the persona can occasionally echo a meme or throw in a short line.

Default:

- minimum interval: 5 minutes;
- random chance: 25%;
- maximum: 10 per hour;
- style: one short meme echo, no essay, no lecture.

This route should arm follow-up listening after it speaks.

