# Operations

This page describes a clean start/stop routine.

## Start Order

1. Start QQ and log in with the small account.
2. Start QCE/NapCat.
3. Confirm OneBot WebSocket is listening.
4. Start the gateway.
5. Confirm the gateway logs incoming group messages.
6. Test with the trigger word.

## Stop Order

1. Stop the gateway first.
2. Stop QCE/NapCat.
3. Close QQ if needed.

Stopping the gateway first prevents half-sent replies and duplicated reconnect behavior.

## Windows to WSL

If QCE/NapCat runs on Windows and the gateway runs in WSL, test connectivity from WSL:

```bash
python3 - <<'PY'
import socket
host = "127.0.0.1"
port = 3001
s = socket.create_connection((host, port), timeout=3)
print("connected")
s.close()
PY
```

If that fails, use the Windows host IP from WSL or run the gateway on Windows.

## Troubleshooting

### The Agent Does Not Reply

Check:

- is QCE/NapCat connected;
- is the gateway receiving messages;
- is the trigger word configured;
- is the group id allowed;
- is the follow-up state expired;
- did the model call timeout.

### It Replies Too Often

Lower:

- random chance;
- max replies per hour;
- follow-up window;
- idle topic trigger.

Raise:

- minimum interval;
- follow-up probability threshold.

### It Replies Too Slowly

Common causes:

- slow vision model;
- web/tool calls inside GenericAgent;
- network from WSL;
- huge context pack.

Use cached image captions and keep the final persona model stable.

