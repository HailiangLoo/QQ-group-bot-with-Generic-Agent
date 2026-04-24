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

## Consent and Platform Safety

Use a small-account listener only where the group expects it. Avoid:

- spammy autonomous replies;
- mass unsolicited messages;
- hidden logging in groups that did not agree to it;
- dumping private profiles into chat;
- exposing raw history when someone asks about another person.

The agent may use memory to speak naturally, but should not reveal the whole memory layer.

