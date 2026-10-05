# Spotify MCP Assistant Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将固定参考版本中的四工具 Spotify MCP 迁移为独立可安装项目，保持现有工具行为与关键测试。

**Architecture:** 复用四个模块，通过包名、导入、配置目录、依赖和 main 入口的最小改动实现独立运行。FastMCP 使用 stdio；确认与播放状态比较继续由助手完成，不引入服务端确认机制。

**Tech Stack:** Python `>=3.10,<4.0`、Poetry/poetry-core、FastMCP `^4.0.10`、httpx `>=0.24.0`、Pydantic `>=2.0.0`、python-dotenv `>=1.0.0`、pytest `>=7.0.0`。

**Spec:** [已批准设计](/Users/kenchen/Projects/spotify-mcp-assistant/docs/superpowers/specs/2026-10-04-spotify-mcp-assistant-design.md)。执行前同时阅读设计和本计划。

## Global Constraints

- 唯一目标仓库：`/Users/kenchen/Projects/spotify-mcp-assistant`；所有项目文件写入与 Git 操作仅在此仓库进行。
- 只读来源：`/Users/kenchen/Projects/modern-software-dev-assignments`；固定提交 `08a96b0c788da2a90e51dd1fac6572f2086b1677`。使用 `git show <commit>:<path>` 读取白名单文件，不运行来源仓库代码或测试。
- 工具恰好为 search_tracks、list_devices、play_track、get_playback_state；签名、模型、annotations、`dry_run=True` 和错误语义保持不变。
- 保留 Authorization Code Flow、固定 `http://127.0.0.1:8888/callback`、原 scopes、提前 60 秒刷新、原子保存及 GET/PUT 重试策略。
- 确认依赖助手指令；不增加服务端确认机制、推荐、相似歌曲、自建聊天界面或无关重构。
- 分发名 `spotify-mcp-assistant`；包名 `spotify_mcp_assistant`；平铺包，不引入额外框架。
- 配置目录 `SPOTIFY_CONFIG_DIR`，缺省 `~/.config/spotify-mcp-assistant`；显式值展开 `~` 后必须绝对；不依赖 cwd。
- 不读取或复制真实 .env、token、.mcp.json；不复制来源 .git、锁文件、课程材料或个人设备信息。
- 复用既有 9 个测试用例，只新增一个聚焦路径解析的测试函数；其余迁移验证用检查命令完成。
- 本计划不授权真实 OAuth、播放或发布；后续真实演示由用户配置和授权后另行进行。

## Review Focus

1. 从非仓库目录启动：安装后的包导入与 stdio 四工具发现正常；任务 1 的 subprocess 检查覆盖。
2. 配置覆盖与路径错误：缺省、绝对路径、`~`、相对路径和空值含义一致；任务 2 的单个路径测试覆盖。
3. 全新配置目录无 token：报告新授权命令，不打开浏览器或创建 token；任务 2 的隔离检查覆盖。
4. 示例注册无法启动或泄漏本机信息：JSON 有效、使用安装环境解释器占位符、新包名且无需 PYTHONPATH；任务 3 的示例检查覆盖。
5. 迁移意外改变工具行为或携带来源文件：四模块 diff、既有协议测试和交付清单检查覆盖；任务 4 验证。

检查范围仅针对迁移；不为 OAuth/API 的未修改分支新增测试体系，不把模拟测试当成真实播放成功。

## 文件映射与职责

| 目标文件（相对目标仓库根） | 来源或职责 |
|---|---|
| pyproject.toml | 新项目安装元数据、必要依赖、包声明和两个 scripts |
| spotify_mcp_assistant/__init__.py | 空包标识，不添加启动副作用 |
| spotify_mcp_assistant/server.py | 复用 week2/server.py；四工具注册与 stdio 入口 |
| spotify_mcp_assistant/oauth.py | 复用 week2/oauth.py；授权、刷新、配置路径与授权入口 |
| spotify_mcp_assistant/spotify_client.py | 复用 week2/spotify_client.py；API 调用与既有错误处理 |
| spotify_mcp_assistant/models.py | 复用 week2/models.py，定义不变 |
| tests/test_mcp_protocol.py | 复用来源同名文件，更新导入与授权提示断言 |
| tests/test_oauth.py | 复用来源同名文件，更新导入，新增一个路径解析测试 |
| .env.example、.mcp.json.example | 来源同名示例的独立项目版本 |
| README.md、.gitignore | 安装与配置说明、对话流程、必要忽略规则 |

以下命令默认在目标仓库运行。测试统一使用新仓库 `.venv/bin/python`；不要使用来源项目虚拟环境。每项检查完成后记录实际结果，再提交该项文件。

### Task 1: 迁移四模块、既有测试与安装入口

**Files:** 创建 pyproject.toml、spotify_mcp_assistant/ 下五个文件、tests/ 下两个文件；按需修改 .gitignore 以忽略 .venv。

**Interfaces:** 消费来源固定提交的源码与测试；产出原有四工具和模型、`server.main() -> None`、`oauth.main() -> None`。安装入口 `spotify-mcp-assistant = spotify_mcp_assistant.server:main`、`spotify-mcp-auth = spotify_mcp_assistant.oauth:main`。

- [x] 从只读提交逐个导出六个 Python 文件：四模块和两个测试；保存到上表目标位置。仅将导入中的 week2 改为 spotify_mcp_assistant，保留通用测试数据。
- [x] 创建空 __init__.py 和 pyproject.toml。沿用 Poetry 元数据格式，version=0.1.0，readme=README.md，声明新包；运行时四个依赖与开发 pytest 使用本计划 Tech Stack 的约束；build-system 沿用 poetry-core>=1.7.0。不复制原作者、课程描述、package-mode=false 或无关依赖。
- [x] 将 server 和 oauth 原 `if __name__ == "__main__"` 中的代码原样移入 main()，保留该 guard 调用 main()；server.main 仍运行 `mcp.run(transport="stdio")`。
- [x] 将源码中旧授权命令替换为 `spotify-mcp-auth`；现有授权错误测试的断言改为包含这个入口名，不改错误码或 retryable 值。
- [x] 使用 Poetry 创建和管理项目内环境：`POETRY_VIRTUALENVS_IN_PROJECT=true poetry env use python3.12`，再用相同设置运行 `poetry install`；生成并提交本项目 poetry.lock。当前 python3 为 3.9.6，使用已检查的 Python 3.12.8。若 FastMCP ^4.0.10 不可解析或解释器不兼容，记录实际错误；不得静默降级或复制来源环境。
- [x] 运行 `.venv/bin/python -m pytest tests -v`，预期既有 9 个用例通过；默认预览用例必须继续断言零 PUT 且不读取真实 token。不要通过删除断言适配迁移。
- [x] 在目标仓库外的临时 cwd 用新环境 Python 验证 `import spotify_mcp_assistant`，清除该检查进程的 PYTHONPATH。使用 FastMCP Client 的 stdio subprocess transport 启动 `python -m spotify_mcp_assistant.server` 并仅调用 list_tools，断言工具名集合恰好为四工具；不调用 Spotify 工具。用安装后的 console script 再检查启动发现，避免入口存在但不可启动。
- [x] 检查安装元数据包含两个 console_scripts，且 oauth.main 可导入；此时不执行授权入口。提交此项：`build: migrate existing Spotify MCP into installable package`。

此项复用测试作为行为基线，不为未修改的模块新增镜像测试；配置位置在任务 2 完成后才达到最终设计。

任务 1 与任务 4 的 stdio 检查使用下面的临时脚本，由待验证环境的 Python 执行（例如 `.venv/bin/python /private/tmp/<本次临时目录>/check_stdio.py`）。不把它加入产品测试目录。StdioTransport 的 command、args、env、cwd 和 keep_alive 参数依据 [FastMCP 官方文档](https://gofastmcp.com/clients/transports)；执行时以安装版本的实际接口为准。

```python
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

os.environ.pop("PYTHONPATH", None)
expected = {"search_tracks", "list_devices", "play_track", "get_playback_state"}

async def check(command, args, cwd):
    transport = StdioTransport(
        command=command, args=args, cwd=cwd, keep_alive=False,
        env={"SPOTIFY_CONFIG_DIR": str(Path(cwd) / "unused-config")},
    )
    async with Client(transport) as client:
        assert {tool.name for tool in await client.list_tools()} == expected

async def main():
    with tempfile.TemporaryDirectory(dir="/private/tmp") as cwd:
        await asyncio.wait_for(check(sys.executable,
            ["-m", "spotify_mcp_assistant.server"], cwd), timeout=30)
        await asyncio.wait_for(check(str(Path(sys.executable).parent /
            "spotify-mcp-assistant"), [], cwd), timeout=30)
    print("PASS: module and console script expose exactly four tools")

asyncio.run(main())
```

### Task 2: 将授权配置移至独立私有目录

**Files:** 修改 spotify_mcp_assistant/oauth.py、tests/test_oauth.py。

**Interfaces:** 新增 `get_config_dir() -> Path`；get_access_token(force_refresh: bool = False) -> str 与 load_config(env_file: Path) -> dict[str, str] 的签名保持不变。oauth.main 与 get_access_token 使用同一目录。

- [x] 在 test_oauth.py 新增一个 `test_config_directory_resolution`，导入 get_config_dir，使用 monkeypatch 和 tmp_path；断言如下（无需读 home 下的文件）：

```python
monkeypatch.delenv("SPOTIFY_CONFIG_DIR", raising=False)
assert get_config_dir() == Path.home() / ".config" / "spotify-mcp-assistant"
chosen = tmp_path / "private-config"
monkeypatch.setenv("SPOTIFY_CONFIG_DIR", str(chosen))
monkeypatch.chdir(tmp_path)
assert get_config_dir() == chosen
monkeypatch.setenv("SPOTIFY_CONFIG_DIR", "~/spotify-mcp-test")
assert get_config_dir() == Path.home() / "spotify-mcp-test"
for invalid in ("relative-config", ""):
    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", invalid)
    with pytest.raises(ValueError, match="SPOTIFY_CONFIG_DIR"):
        get_config_dir()
```

- [x] 运行 `.venv/bin/python -m pytest tests/test_oauth.py -v`，预期新增测试因缺失 get_config_dir 失败；确认不是依赖或环境失败。
- [x] 实现 get_config_dir：环境键缺失用默认路径；键存在则 Path(value).expanduser()，空值或非绝对路径抛 ValueError 且消息含变量名。不创建目录，不加载配置，不解析来源仓库路径。
- [x] 将 oauth 中两处配置/token 路径统一改用该函数。oauth.main 先 `mkdir(parents=True, exist_ok=True)`，再调用原授权流程；get_access_token 不创建目录。文件名仍是 .env 与 .spotify_token.json，保存与刷新算法不变。
- [x] 运行 `.venv/bin/python -m pytest tests -v`，预期 10 个用例通过：既有 9 个，加 1 个配置目录解析测试。
- [x] 从临时 cwd 运行隔离检查，SPOTIFY_CONFIG_DIR 指向临时目录下不存在的子目录。调用 get_access_token，断言 AuthorizationRequiredError 和消息含 spotify-mcp-auth，且子目录仍未创建。检查只触及该临时路径，不读取默认私有目录。
- [x] 将 load_config、receive_authorization_code、exchange_code 和 save_token 用检查脚本临时替换为记录调用的假函数，执行 oauth.main；断言 env/token 的路径都在临时配置目录、目录已创建、没有真实 HTTP 或浏览器调用。无需新增持久测试文件。
- [x] 审查两处路径调整和授权提示，提交：`fix: isolate Spotify configuration and token paths`。

### Task 3: 示例配置与产品使用说明

**Files:** 创建 .env.example、.mcp.json.example；修改 README.md、.gitignore。

**Interfaces:** 文档描述任务 1 的安装入口与任务 2 的配置目录；MCP 示例使用新包模块启动，不依赖 PYTHONPATH。

- [x] 从固定提交读取两个 example 文件后仅写入目标项目；.env.example 凭证值为空，redirect URI 保持 `http://127.0.0.1:8888/callback`。
- [x] .mcp.json.example 保留原 stdio 结构；command 使用 `/ABSOLUTE/PATH/TO/VENV/bin/python`，args 为 `["-m", "spotify_mcp_assistant.server"]`；env 仅设置可选的 SPOTIFY_CONFIG_DIR 绝对路径占位符，删除 PYTHONPATH。不得设置 client secret 或 token。
- [x] 编写 README：定位与四工具表、独立安装步骤、两个命令入口、私有目录配置方式、由用户填写新凭证并自行授权的步骤、MCP 注册示例、从搜索到确认和验证的完整流程、常见错误恢复、测试命令。说明 preview 的校验范围、从头播放、submitted 与已验证的区别、确认属于助手指令。
- [x] 保留现有 `.gitignore` 的适用规则；补齐真实 .env、.spotify_token.json、.mcp.json、.venv、__pycache__、.pytest_cache 的忽略项，确保 example 文件未被忽略。
- [x] 用 Python json 模块解析 .mcp.json.example，断言命令/args/env 与上面一致。用 `git check-ignore --no-index` 检查真实文件名被忽略而 example 可跟踪，检查不需要创建或打开任何真实文件。
- [x] 通读 README 与两个示例：命令、回调、配置路径、包名一致；没有课堂提交步骤、个人设备、真实结果或凭证。提交：`docs: document standalone setup and MCP workflow`。

### Task 4: 最终迁移验证与交付

**Files:** 无新增产品文件；仅修正上述迁移范围内发现的问题。

**Interfaces:** 消费完成后的独立包、测试、入口和示例；产出验证记录与可审查的迁移 diff。

- [x] 运行完整 `.venv/bin/python -m pytest tests -v`，预期 10 个用例通过；如失败，先定位根因，不增加无关重构或测试。
- [x] 在 `/private/tmp` 的一次性验证环境中执行非 editable 安装：创建独立 venv，使用其 Python `-m pip install /Users/kenchen/Projects/spotify-mcp-assistant`。从该目录外导入新包并执行任务 1 的 stdio 四工具发现检查，移除检查进程的 PYTHONPATH。证明安装不借助仓库 cwd 或 editable 链接；只调用 list_tools，不读取配置或联系 Spotify。检查后清理本次创建的临时环境。
- [x] 用 `git show` 分别读取来源四模块，与目标文件逐一比较。models.py 应完全一致；其他 diff 仅允许包导入、配置路径、main 入口和授权提示。检查 GET 重试、PUT 分支、模型/schema、默认 dry_run、annotations 和确认指令没有改变。
- [x] 用 `git ls-files` 和限定文件清单检查目标交付：无真实配置、token、课堂材料、来源 .git 或个人设备数据。文本扫描只针对已跟踪的源码、测试、README 和 example，不扫描实际 .env/token。设计与计划中的来源说明不算运行时依赖。
- [x] 运行 `git diff --check`，检查目标 `git status --short`，记录新项目测试和安装结果。不得通过在来源仓库运行 Git 写命令来验证只读；所有来源调用始终限定为读取固定提交。
- [x] 如有修正，提交 `fix: address migration verification findings`；交付报告包含变更摘要、测试数量、stdio/安装检查结果、继承的局限。真实 OAuth 和播放尚未验证时明确标为未验证。

## 执行与审阅

推荐当前会话直接执行（Native）：这四项高度依赖同一组模块与路径，迁移范围小，连续执行便于控制 diff。若选择 Subagent-driven，可按任务逐项委派与审阅；选择前不启动子代理。

用户已选择当前会话执行，并确认使用 Poetry。实现已在目标仓库 codex/spotify-mcp-migration 分支完成；所有提交限定在目标仓库，没有推送或发布。


## 执行验证记录

- Poetry 2.5.1 管理项目 .venv，Python 3.12.8，FastMCP 4.0.11；新生成 poetry.lock。
- 既有 9 个用例通过；新增配置路径测试先因缺失解析函数失败，实现后完整 10 个用例通过。
- 临时目录验证缺 token 不创建目录、不打开浏览器；mock 授权入口验证 env/token 路径一致。
- 两个示例可解析且不含凭证；真实配置与缓存路径被忽略，example 可跟踪。
- Poetry sdist/wheel 构建成功；全新临时环境按锁定版本安装 wheel 成功，随后从仓库外通过模块和 console script stdio 发现恰好四工具。临时安装环境已清理。
- models.py 与参考提交完全一致；其他模块 diff 仅为迁移范围内调整。
- Poetry 2 的旧元数据弃用提示不阻止安装、校验或构建；沿用已批准格式，后续可单独更新。
- 没有真实 OAuth、读取真实凭证/token、连接 Spotify API 或执行播放；实际账户与设备验收留给用户自行配置后进行。
- 独立代码审阅完成：无 Critical/Important/Minor 问题；审阅者独立复核 10 个测试、外部 cwd 两个 stdio 入口、缺 token 无副作用、示例配置和源码复用范围。最终非 editable 安装由主执行者另行验证通过。
- 审阅保留的边界：真实 OAuth/账户资格/播放未验证；服务端确认不在本版；损坏 token、超时和错误归一化沿用来源限制；Poetry 2 元数据弃用提示后续再处理。
