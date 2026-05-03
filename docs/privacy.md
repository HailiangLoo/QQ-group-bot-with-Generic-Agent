# Privacy and Open Source Hygiene

This repository is designed to be safe to publish, but only if private data stays out.

## Never Commit

- API keys;
- QQ passwords;
- real QQ ids, group ids, openids, or account tokens;
- raw chat exports;
- real member profiles;
- private inside jokes tied to identifiable people;
- screenshots from private groups;
- live SQLite databases.

## Keep In Private Deployment Data

Put private runtime data outside the repo or under ignored folders:

```text
data/
private/
runtime/
```

By default the public gateway should not store raw OneBot event payloads. If raw events are needed for local debugging, redact transport fields such as `url`, `file`, `path`, `cookie`, and `token`, and keep the resulting database out of git.

QQ file segments are especially sensitive. A safe public default is:

- image-like file segments may be treated as images if the extension and size are plausible;
- normal files, audio, and video should be represented as `[QQ文件/音视频已屏蔽]`;
- the agent should not read or upload arbitrary QQ files just because a group member asks.

## Consent and Platform Safety

Use a small-account listener only where the group expects it. Avoid:

- spammy autonomous replies;
- mass unsolicited messages;
- hidden logging in groups that did not agree to it;
- dumping private profiles into chat;
- exposing raw history when someone asks about another person.

The agent may use memory to speak naturally, but should not reveal the whole memory layer.

## Prompt Injection Boundary

QQ messages are user input, not operator instructions. A group member should not be able to make the agent:

- read local files;
- expose logs or config;
- reveal keys/cookies/tokens;
- rewrite long-term memory without review;
- dump raw chat history or private profiles.

The open-source skeleton therefore keeps arbitrary local tools out of the default runner. Add tools only behind explicit allowlists.
