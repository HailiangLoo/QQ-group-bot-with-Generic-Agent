# Group Memory Agent 中文说明

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

## 触发方式

默认设计：

- 显式喊 `杰出`：直接回复。
- 杰出刚说完后：监听接下来 6 条消息，判断是否有人还在跟它说。
- 群里静默 15 分钟后有人开新话题：等对方说完，120 秒没人接，杰出可自然接一句。
- 长文本超过 300 字：等 45 秒没人接，尝试摘要或提炼重点。
- 关键词/随机接梗：5 分钟最小间隔，每小时最多 10 次，随机概率 25%，只短接梗。

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

