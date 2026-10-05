# Spotify MCP Assistant 第一版迁移设计

状态：用户已批准（2026-10-04）；本文件是设计，不是实施计划。日期：2026-10-04。

## 1. 目标与来源

把已经实现的 Spotify Playback MCP 迁移为可独立安装、配置和启动的 Python 项目，面向工作时明确找歌、选择设备并播放的场景。通过现有 MCP 客户端对话展示独立产品开发和 AI 工具开发能力，复用已验证的工具设计与 API 行为。

目标仓库：`/Users/kenchen/Projects/spotify-mcp-assistant`。

只读来源：`/Users/kenchen/Projects/modern-software-dev-assignments`，固定提交 `08a96b0c788da2a90e51dd1fac6572f2086b1677`（Complete week2 Spotify playback MCP assignment）。迁移内容以此提交的文件为准，不取参考仓库工作区的最新内容。

已通过 `git show` 阅读该提交的 server.py、oauth.py、spotify_client.py、models.py、tests/ 下两个测试文件、两个示例配置、writeup.md 和根 pyproject.toml。没有读取真实 .env、token 或 .mcp.json。writeup 中的个人设备名称与 ID 仅用于理解既有行为，不进入新项目文档或测试数据。

用户已确认的边界：独立 Python 项目、FastMCP stdio、恰好四个现有工具、默认 dry_run=true、由助手指令要求确认、不增加服务端确认机制。第一版不做推荐、相似歌曲、自建聊天界面、暂停/续播工具、播放队列或播放列表管理。

本设计新增的提案：可安装的平铺包、两个命令入口、独立的私有配置目录。它们只解决独立运行，不改变工具行为。

## 2. 迁移方式选择

| 方式 | 收益 | 代价与判断 |
|---|---|---|
| **推荐：复制明确源码清单，转换为可安装包** | 保持四工具契约；正常安装后不依赖启动目录或 PYTHONPATH；迁移 diff 易审查 | 需要调整导入、配置位置和两个入口，均属于本版范围 |
| 复制脚本目录，继续用 PYTHONPATH 启动 | 改动较少 | 仍依赖客户端配置包搜索路径，独立安装和使用体验较弱 |
| 重写客户端或增加服务层、确认状态机 | 可改变架构与行为 | 超出迁移目标，不采用 |

采用第一种。保留现有四模块职责，不引入额外框架、异步重写、依赖注入层或通用错误框架。

## 3. 可复用内容与必要调整

| 来源 | 可直接复用的逻辑 | 必须调整的内容 |
|---|---|---|
| server.py | FastMCP 实例、四工具名称与 schema、默认值、annotations、结构化错误包装、确认与验证指令、stdio transport | `week2` 导入替换为 `spotify_mcp_assistant`；将启动语句封装为 main()，支持命令入口和模块启动 |
| oauth.py | Authorization Code Flow、随机 state、回调校验、令牌交换、提前 60 秒刷新、保留旧 refresh_token、临时文件加 os.replace 原子保存、禁止工具触发交互授权 | `.env` 与 token 从模块旁移至私有配置目录；统一配置路径解析；授权入口 main()；旧授权命令提示更新；授权时创建配置目录 |
| spotify_client.py | HTTP 调用、15 秒超时、GET 401 至多一次刷新重试、设备检查、dry_run 分支、单曲 PUT、禁止写操作自动重试、现有错误码和恢复提示 | 包导入与含旧路径的授权提示；不改变 API 请求体或重试语义 |
| models.py | 全部 Pydantic 模型、字段与 nullable 行为 | 移入新包；模型定义保持原样 |
| tests/test_mcp_protocol.py | 工具发现、nullable 设备 ID、默认预览零 PUT、limit 校验、限流错误、204 状态、授权失败测试 | 更新导入；授权提示断言从旧 oauth.py 改为新授权命令；保留通用假设备与假 token |
| tests/test_oauth.py | 缺配置时报告变量名的测试 | 更新导入，继续用 tmp_path 和清空环境变量；不使用真实配置 |
| .env.example | 三个配置变量与 loopback redirect URI | 放于新仓库根目录；保持凭证值为空，说明复制到私有配置目录 |
| .mcp.json.example | stdio 注册方式和绝对解释器路径占位符 | 模块名改为新包；安装后移除 PYTHONPATH；可选配置目录用占位符，禁止具体个人路径 |
| writeup.md | 工具组合、确认边界、失败恢复的产品说明 | 改写为独立项目 README 的必要说明；不复制课堂结构、提交说明、个人 transcript 或历史成功声明 |
| pyproject.toml | Python 范围、FastMCP、Pydantic、dotenv、httpx 和 pytest 相关依赖 | 新名称、描述、安装包声明与 scripts；httpx 是运行时依赖；移除课程项目及无关依赖 |

迁移只按文件白名单进行，不复制整个来源目录，不复制原 .git、assignment.md、practice、其他周作业、课堂材料、虚拟环境或真实配置。既有 writeup 提到的 client.py 不在本次复用清单内，不新增第五个工具或额外客户端应用。

## 4. 工具契约与对话流程

| 工具 | 参数 | 返回与行为 |
|---|---|---|
| search_tracks | query：去空白后非空；limit 默认 5，范围 1–10 | 歌名、歌手列表、track_uri、Spotify URL；空列表表示无匹配；只搜索 track |
| list_devices | 无 | device_id 可为 null，另含名称、类型、active/restricted 标志；列设备不会切换设备 |
| play_track | track_uri：22 位 Spotify track ID 的 URI；device_id 非空；dry_run 默认 true | 预览返回 preview、URI、设备 ID、设备名和 next_action；真实写入成功仅返回 submitted |
| get_playback_state | 无 | has_playback、is_playing、progress_ms、歌曲与设备；204 返回没有可用播放状态 |

所有业务结果保留 `ok/data/error` 包装；错误保留 code、message、next_action、retryable 和可选 retry_after_seconds。MCP schema 校验失败与 `ok=false` 业务失败保持既有区别。

正常流程：

1. 用户明确指定歌曲或歌手。助手调用 search_tracks；只有歌手时展示该搜索结果，由用户选择要播放的歌曲，不把搜索包装成推荐。
2. 助手调用 list_devices。多首版本、翻唱或多个设备存在歧义时让用户选择，不自行猜测。device_id=null 或 restricted=true 的设备不可作为播放目标。
3. 助手用所选 URI 和设备 ID 调用 play_track，默认 dry_run=true。展示来自搜索结果的歌名、歌手、链接，以及预览返回的设备名和 ID。
4. 助手停止，等待**预览之后的新用户消息**确认该歌曲和设备。最初的“播放这首歌”不替代确认。若选择改变，重新预览并等待新的确认。
5. 以相同 URI 和设备 ID 调用 dry_run=false。服务端再次查询设备并检查可用性，然后发出一次播放 PUT。
6. 助手调用 get_playback_state，比较 track_uri、device_id 和 is_playing。只有歌曲、设备匹配且 is_playing=true，才报告已验证播放。无状态、字段缺失或不匹配时，报告当前观察和未验证结果。

“预览”是执行预览，不是音频试听。原实现仅校验 URI 格式、设备存在与不受限制；它不验证歌曲存在、地区可播性或账户权限。预览会调用设备读取 API，因此仍需授权和网络连接。

确认依赖 FastMCP instructions 和工具 docstring。服务端不会验证聊天记录，也不会阻止客户端直接传 dry_run=false。annotations 是客户端提示，不是授权控制。本版明确保留这一边界，不增加确认 token、会话状态或持久化审批记录。

play_track 是从头播放，不是恢复进度。submitted 表示写请求成功返回，不能直接当作歌曲和设备已经验证。

## 5. 架构与独立运行

数据流：现有 MCP 客户端 → FastMCP stdio server → spotify_client → Spotify Web API。API 客户端向 oauth 获取 access token；models 定义工具输出。交互授权由独立命令运行。

建议项目结构：

```text
spotify-mcp-assistant/
  pyproject.toml
  README.md
  .gitignore
  .env.example
  .mcp.json.example
  spotify_mcp_assistant/
    __init__.py
    server.py
    oauth.py
    spotify_client.py
    models.py
  tests/
    test_mcp_protocol.py
    test_oauth.py
  docs/superpowers/specs/
    2026-10-04-spotify-mcp-assistant-design.md
```

使用来源已有的 Poetry/poetry-core 打包方式，但启用安装包模式。分发名 `spotify-mcp-assistant`，Python 包名 `spotify_mcp_assistant`。运行时直接声明 fastmcp、httpx、pydantic、python-dotenv；开发测试只需 pytest。FastMCP 首先沿用来源声明 `^4.0.10`，迁移时验证依赖能解析；若不能解析，要记录具体兼容性问题，不能静默降级并宣称等价。不复制参考项目的完整锁文件或无关依赖。

两个入口：

- `spotify-mcp-assistant` → server.main，启动 stdio MCP。
- `spotify-mcp-auth` → oauth.main，用户主动运行一次授权。

保留模块启动 `python -m spotify_mcp_assistant.server` 和 `python -m spotify_mcp_assistant.oauth`。README 说明在独立虚拟环境安装后启动；MCP 示例使用该环境绝对 Python 路径加新模块名，无需 PYTHONPATH。stdout 留给 MCP 协议，授权命令原有终端输出不进入服务进程。

## 6. 配置与授权路径

配置目录由 `SPOTIFY_CONFIG_DIR` 指定；不设置时默认 `~/.config/spotify-mcp-assistant`。显式设置必须是绝对路径，支持展开 `~`；错误路径清楚报错，不猜测来源仓库位置。

该目录包含用户自行创建的 `.env` 和授权命令新生成的 `.spotify_token.json`。代码加载这个明确的 env_file，不搜索上级目录，不读取原仓库文件。环境中的既有变量优先级沿用 load_dotenv 默认行为。

保持三个变量：SPOTIFY_CLIENT_ID、SPOTIFY_CLIENT_SECRET、SPOTIFY_REDIRECT_URI。继续使用原 Authorization Code Flow，不改为 PKCE。现有回调监听固定 `127.0.0.1:8888` 且路径为 `/callback`；README 和示例必须使用 `http://127.0.0.1:8888/callback`，不暗示支持任意端口或路径。

oauth.main 在授权时创建目标目录；工具读取缺失 token 时只返回授权提示，不创建交互流程。新 token 必须通过新项目授权生成，不从旧项目迁移。继续采用同目录临时文件原子替换，不改变保存算法。

.gitignore 保证忽略真实 .env、token cache、.mcp.json、虚拟环境与测试缓存，同时允许提交两个 example 文件。示例、文档和测试仅使用空值、通用假数据与路径占位符，不写入个人设备名称、ID 或秘密。

## 7. 错误、恢复与已有局限

保留 auth_required、oauth_config_error、forbidden、not_found、rate_limited、spotify_error、network_error、invalid_track、device_unavailable、device_restricted 和 playback_result_unknown 等现有错误语义。

- GET 返回 401 时至多强制刷新并重试一次；工具不会打开授权浏览器。
- PUT 不自动刷新后重发或自动重试，重复播放可能从头开始。
- 写请求网络失败且可能已发送时返回 playback_result_unknown，先读状态再决定下一步，不能直接重放。
- 设备消失或受限制时停止，让用户刷新设备和选择目标，不自动切到别的设备。
- 429 展示 Retry-After；不建立后台重试任务。
- submitted 后状态可能延迟。助手可短暂等待后再次只读查询；本版不加服务端轮询或自动回滚，不把未验证说成失败或成功。

原 oauth 对所有配置错误或损坏 token 文件并未统一转换为 SpotifyError；本版不承诺新增这类错误覆盖。端口占用、授权超时等保持授权命令现有失败行为。这些是继承的限制，不以迁移之名扩展重构。

外部运行前提包括 Spotify 应用访问资格、所需 scopes、Premium 播放账户与可见且可控的设备。官方播放接口要求 Premium；新项目设计阶段未连接真实 Spotify 账户，未验证应用资格或真实设备可用性。[播放接口文档](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback)

## 8. 验证范围与验收标准

来源包含两个测试文件、9 个参数化用例（8 个协议用例和 1 个配置用例）。本次已阅读测试源码，没有运行参考项目测试。原 writeup 的通过记录属于历史来源证据，不能当作新项目已经通过。

直接保留这些测试，更新包导入和授权提示断言。它们验证四工具发现与 structured output、普通/nullable 设备 ID、搜索到默认预览的组合且零 PUT、limit=0/11 拒绝、结构化限流错误、204 空状态和缺授权/配置情况。

现有测试没有覆盖完整 OAuth 刷新、真实播放、用户确认遵循或写入结果未知的全部分支，不声称具备这些覆盖。第一版不扩展为完整新测试体系。

迁移需要的新增验证仅针对迁移本身：在隔离环境中安装新包；从非仓库目录启动并发现恰好四个 stdio 工具；用临时配置目录验证路径选择不依赖 cwd。必要时只增加一个聚焦配置目录解析的小测试，不访问真实凭证或网络。安装与命令检查用检查命令完成，不为脚本和元数据重复写测试。

验收条件：

1. 新仓库源码、导入、运行指令、示例配置不再依赖 week2 或来源仓库。
2. 可安装并通过 stdio 启动，工具名称、输入输出与默认预览行为保持不变。
3. 迁移后的既有 9 个测试通过；dry_run 继续不发送 PUT。
4. 独立配置目录、授权命令与 MCP 启动入口在文档中一致。
5. 源码与参考提交 diff 仅体现包、导入、配置路径、提示、依赖和入口所需调整。
6. 新项目不含课程文件、个人设备数据、真实凭证或 token；参考仓库不发生任何写入。

真实对话演示属于后续用户自行配置并授权后的验收：搜索、选择、预览后停止、新消息确认、一次播放请求、状态验证。演示只记录必要的脱敏结果，不能把模拟测试当作实时播放成功。

## 9. 审阅焦点与后续

请重点审阅：可安装平铺包与两个命令入口、私有配置目录的默认位置、保留助手确认而非服务端确认，以及严格限制迁移 diff 的范围。

设计批准后再制定文件级迁移实施计划，说明操作顺序、来源映射、验证命令和交付检查。本阶段不复制源码、不安装依赖、不生成凭证、不执行播放。
