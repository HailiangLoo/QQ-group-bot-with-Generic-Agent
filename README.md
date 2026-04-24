# QQ 群 Generic Agent 机器人

English：[README.en.md](README.en.md)。

这是一个从当前实验版里抽出来的干净项目骨架，用来整理 QQ 小号、QCE/NapCat、OneBot、WSL、GenericAgent、图片识别和群记忆之间的关系。

这个仓库不放真实群聊数据、不放 API key、不放 QQ 账号密码、不放人物画像。它只放通用架构、接口边界、示例配置和可复用代码壳。

## 一句话架构

```text
QQ 小号负责看群
QCE/NapCat 负责把 QQ 消息变成 OneBot 事件
group-memory-agent 负责存消息、看图缓存、触发策略、组装上下文
GenericAgent / LLM runner 负责最终思考和人格回复
OneBot 再把回复发回群里
```

## 为什么要这样拆

之前实验版里很多东西混在一起：

- QQ 接入；
- 图片识别；
- V4 Flash 回复；
- Qwen 看图；
- deep profiles；
- 触发策略；
- 自动插话；
- live memory；
- GenericAgent 任务循环。

混在一起能跑，但以后会越来越难维护。这个干净仓库把它拆成几个稳定边界：

| 模块 | 职责 |
| --- | --- |
| QQ 小号 | 作为普通群成员看到群消息 |
| QCE/NapCat | 把 QQ 消息转成 OneBot WebSocket |
| OneBot gateway | 收消息、发消息、解析图片段 |
| live memory | 保存最近可见消息 |
| image cache | 图片 hash 去重，缓存 Qwen 图片描述 |
| trigger policy | 决定什么时候该回 |
| main runner | 调 GenericAgent 或主文本模型 |
| deep profiles | 离线/定期学习出来的长期记忆 |

## 这个项目提供什么

- OneBot / QCE / NapCat 的接入边界。
- 群消息 live memory 的 SQLite 存储壳。
- 图片 hash 去重和图片描述缓存。
- “主模型稳定人格，视觉模型只做看图”的路由设计。
- 触发策略：
  - 显式触发词；
  - bot 说话后的短窗口跟聊；
  - 沉默后新话题自动接一句；
  - 长文本摘要；
  - 低频关键词 / 随机接梗。
- 上下文包和群聊回复 prompt 的示例结构。
- QCE、WSL、OneBot、GenericAgent、模型路由之间的关系文档。

## 这个项目不包含什么

- 真实 QQ 聊天记录。
- 真实群成员画像、关系总结、episodes 或 live memory。
- API key。
- QQ 账号、密码、cookie、token。
- 群号、用户 ID、openid、真实昵称、别名。
- 会暴露真实群社交结构的私有 prompt。

## 当前推荐路线

### 文本人格核心

主回复统一走 DeepSeek V4 Flash thinking，保持“杰出”的人格稳定。

### 图片

每张新图片先交给便宜快速的视觉模型生成描述，例如 Qwen vision flash。

同一张图下次出现时直接读缓存，不再重复看图。

图片描述会作为上下文交给 V4 Flash，最终发言仍由 V4 Flash 生成。

### 长期记忆

群聊历史不要每次全塞。运行时只给：

- 最近上下文；
- 图片描述；
- 相关人物短档案；
- 重要事件 / 偏好；
- 当前触发原因。

Deep profiles 和 episodes 应该定期更新，不要和实时回复阻塞在一起。

## 启动关系

推荐顺序：

1. Windows 打开 QQ 小号。
2. 启动 QCE/NapCat。
3. 确认 OneBot WebSocket 地址，例如 `ws://127.0.0.1:3001`。
4. 启动 gateway。
5. gateway 调 GenericAgent 或主模型。
6. 群里用触发词测试。

如果 gateway 在 WSL 里跑，要注意 `127.0.0.1` 可能不是 Windows 的 localhost。遇到连不上，就改成 Windows host IP，或者直接在 Windows 跑 gateway。

## 从零开始怎么跑

### 1. 克隆和安装

```powershell
git clone https://github.com/HailiangLoo/QQ-group-bot-with-Generic-Agent.git
cd QQ-group-bot-with-Generic-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Linux / WSL：

```bash
git clone https://github.com/HailiangLoo/QQ-group-bot-with-Generic-Agent.git
cd QQ-group-bot-with-Generic-Agent
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

### 2. 复制配置

```powershell
Copy-Item examples\config.example.toml config.toml
```

或者：

```bash
cp examples/config.example.toml config.toml
```

然后改 `config.toml`：

- `onebot.ws_url`：QCE/NapCat 的 OneBot WebSocket 地址。
- `onebot.trigger_words`：触发词，默认是 `杰出`。
- `onebot.allowed_groups`：建议正式运行时改成具体群号。
- `memory.db_path`：live memory SQLite 路径。
- `models.text`：最终人格回复模型。
- `models.vision`：图片描述模型。

### 3. 准备 QCE / NapCat

1. Windows 打开 QQ 小号并登录。
2. 启动 QCE/NapCat。
3. 打开 OneBot WebSocket。
4. 记下地址，通常是：

```text
ws://127.0.0.1:3001
```

如果 gateway 在 WSL，`127.0.0.1` 可能连不到 Windows。遇到这种情况，要么让 gateway 在 Windows 跑，要么把 `ws_url` 改成 WSL 能访问的 Windows host 地址。

### 4. 启动 gateway

```bash
python scripts/run_onebot_gateway.py --config config.toml
```

当前干净骨架默认用 `StubAgentRunner`，只会回一条调试文本。它的作用是确认 OneBot 接通、消息能收到、触发词生效。

要接入真实 GenericAgent，需要实现 `src/group_memory_agent/runner.py` 里的 `AgentRunner.reply()`。

### 5. 群里测试

群里发：

```text
杰出 你好
```

如果看到 stub 回复，说明链路通了：

```text
[stub:explicit trigger word] 我收到了：杰出 你好
```

然后再把 runner 换成真实 GenericAgent 或 OpenAI-compatible chat completion。

## 触发方式

默认设计：

- 显式喊 `杰出`：直接回复。
- 杰出刚说完后：监听接下来 6 条消息，判断是否有人还在跟它说。
- 群里静默 15 分钟后有人开新话题：等对方说完，120 秒没人接，杰出可自然接一句。
- 长文本超过 300 字：等 45 秒没人接，尝试摘要或提炼重点。
- 关键词/随机接梗：5 分钟最小间隔，每小时最多 10 次，随机概率 25%，只短接梗。

## 图片处理机制

推荐链路是：

```text
图片文件
  -> 计算 SHA-256 hash
  -> 查 image cache
  -> 缓存命中：直接取历史图片描述
  -> 缓存未命中：调用视觉模型生成图片描述
  -> 把图片描述写成文本上下文
  -> 主人格模型生成最终群聊回复
```

视觉模型不要直接扮演群友发言。它只负责观察图片，例如：

- 图片类型：截图、表情包、聊天记录、游戏画面、网页、照片等；
- 可见主体、人物、物品、界面；
- OCR 文本；
- 可能的软件、网站、logo、游戏或应用；
- 图里的笑点、梗点、上下文线索；
- 不确定的地方要明确说不确定。

最终回复仍由主文本模型生成。这样图片再多，人格也不会因为视觉模型切来切去而飘。

## 记忆层设计

运行时不要把 5 万行历史聊天全塞给模型。建议分三层：

```text
live_memory.db
  最近可见消息
  图片描述缓存
  轻量运行时事实

deep_profiles/
  每个成员的长期画像
  兴趣、偏好、说话方式、关系模式、重要生活线索

episodes.jsonl
  重要事件
  纠错和偏好变更
  关系场景
  值得复用的群内梗
```

每次回复时只组装一个 compact context pack：

- 最近几十条可见上下文；
- 当前消息和图片描述；
- 被提到成员的相关短档案；
- 相关 episodes；
- 用户最近纠正过的偏好；
- 当前触发原因。

deep profiles 和 episodes 的更新应该走离线或低频后台任务，不要阻塞实时聊天回复。

## 接入真实 GenericAgent

`AgentRunner` 是接入边界：

```python
class AgentRunner(Protocol):
    async def reply(self, request: ReplyRequest) -> str:
        ...
```

你可以把它实现成：

- 调用 GenericAgent 子进程；
- 调 OpenAI-compatible chat completion；
- 调本地模型；
- 调你自己的 agent loop。

gateway 负责收消息、存上下文、处理图片、判断触发；runner 只负责“拿到上下文包，返回最终要发到群里的话”。

## Windows 启动脚本

仓库里有模板：

```text
scripts/windows/start-qce.example.bat
scripts/windows/start-gateway-wsl.example.bat
```

复制后再改成本机路径：

```powershell
Copy-Item scripts\windows\start-qce.example.bat scripts\windows\start-qce.bat
Copy-Item scripts\windows\start-gateway-wsl.example.bat scripts\windows\start-gateway-wsl.bat
```

改过的本地脚本如果包含真实路径、账号名或密钥，不要提交。

## 私有数据应该放哪

私有部署可以放在仓库外，或者放进被 `.gitignore` 忽略的目录：

```text
data/
private/
private_memory/
```

不要提交：

- API key；
- QQ 密码；
- 群号；
- 用户 ID；
- 原始聊天记录；
- deep profiles；
- live SQLite；
- 图片缓存；
- 真实成员别名。

## 下一步接入实验版

这个项目现在是干净骨架。要接你的实验版，可以逐步迁移：

1. 把现有 OneBot 收发逻辑搬进 `onebot_gateway.py`。
2. 把图片 hash + Qwen caption cache 搬进 `image_cache.py`。
3. 把当前触发策略搬进 `trigger_policy.py`。
4. 把 GenericAgent 调用封装成一个 `AgentRunner`。
5. 把 deep profiles 检索做成 runner 前的 memory retrieval。

这样最后可以做到：外层干净，私有群记忆只作为部署数据挂载。

## 常见问题

### gateway 启动了，但收不到消息

- QCE/NapCat 没连上 QQ。
- OneBot WebSocket 地址写错。
- gateway 在 WSL，`127.0.0.1` 指向了 WSL 自己，不是 Windows。
- QCE/NapCat 没开启对应事件。
- 收到的不是群消息事件。

### 能收到消息，但 bot 不回复

- 触发词不匹配。
- 当前群不在 `allowed_groups`。
- runner 还是 stub。
- 触发策略判断为不该回。
- bot 正处于静默 / 禁言窗口。

### 回复太频繁

降低：

- `auto_reply_chance`；
- `auto_reply_max_per_hour`；
- follow-up 监听条数。

提高：

- `auto_reply_min_interval`；
- follow-up 概率阈值；
- 新话题等待时间。

### 图片回复人格不稳定

不要让视觉模型直接写最终回复。视觉模型只产出图片描述，最终仍交给主文本模型说话。

## 文档目录

- [架构说明](docs/architecture.md)
- [QCE、WSL、OneBot、GenericAgent 的关系](docs/qce-wsl-genericagent.md)
- [触发策略](docs/trigger-policy.md)
- [记忆设计](docs/memory-design.md)
- [运行维护](docs/operations.md)
- [隐私和开源清理](docs/privacy.md)

## License

MIT.
