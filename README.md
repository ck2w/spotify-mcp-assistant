# 🎵 Spotify MCP Assistant

**Your music, playlists, and playback — one conversation away.**

A Python MCP server that lets your AI client search Spotify, build playlists, control playback, manage the queue, and save your favorite songs.

🤖 **Claude Desktop · Claude Code · Codex · Cursor**<br>
🧰 **32 tools** · 🍎 **macOS setup wizard** · 📦 **Version 0.3.0**

The AI client handles the conversation and chooses tools. This project connects those tools to Spotify using **FastMCP over stdio**.

## ✨ What can you do?

| | Try asking… |
|---|---|
| 🔎 Find music | “Find Coldplay's Yellow and show me the available versions.” |
| 🎶 Build a playlist | “Help me create a private Commute playlist with these songs.” |
| ✏️ Organize playlists | “Show this playlist's tracks, then preview moving the last song to the top.” |
| 🔊 Control playback | “List my devices and help me play this playlist on my laptop.” |
| ⏯️ Adjust the player | “Pause the music.” · “Set the volume to 30%.” · “Turn shuffle on.” |
| ➕ Manage the queue | “Show the queue, then preview adding this song.” |
| ❤️ Manage favorites | “Check which of these songs I've saved, then preview saving the rest.” |

For playlist edits, favorites, queue additions, and starting or transferring playback, ask your client to **preview → wait for confirmation → execute → check the result**. Clear requests for direct player controls run immediately on a selected device.

## 🧭 Jump to

- [🚀 Quick start](#-quick-start-macos)
- [💬 Your first conversation](#-your-first-conversation)
- [🧰 All 32 tools](#-all-32-tools)
- [🔐 Credentials & account sharing](#-credentials--account-sharing)
- [🛠️ Troubleshooting](#-troubleshooting)
- [👩‍💻 Manual setup & development](#-manual-setup--development)

## 🚀 Quick start (macOS)

### ✅ Before you start

You need:

- One of the four clients listed above.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) to install the Python tool.
- Your own [Spotify Developer App](https://developer.spotify.com/dashboard), including its **Client ID** and **Client Secret**.
- A Spotify account with access to that app. **Playback requires Premium.**

> 📦 **0.3.0 is not yet published to PyPI.** Get the wheel from the maintainer, or build it from source using `poetry build`. The commands below install that local file.

### 1️⃣ Install the package

Replace the placeholder with the absolute path to your wheel:

```bash
uv tool install --python 3.12 /ABSOLUTE/PATH/spotify_mcp_assistant-0.3.0-py3-none-any.whl
```

uv prepares Python and a persistent tool environment. You do not need Poetry or a source checkout when using a supplied wheel.

### 2️⃣ Run the setup wizard

```bash
uvx --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup
```

After installation, uvx reuses that installed version. Run this in an **interactive terminal**.

The wizard walks you through:

- 🤖 Choosing one or more clients.
- 🔑 Entering your Spotify app credentials; the secret prompt is hidden.
- 🌐 Authorizing your account in the browser.
- 🧪 Checking authorization and discovering all 32 MCP tools.
- 💾 Backing up and merging your client configurations.

In your Spotify app settings, register this **exact** redirect URI:

```text
http://127.0.0.1:8888/callback
```

Keep port **8888** available. Use `127.0.0.1` exactly as shown.

💡 Already know which clients you want? Select them directly:

```bash
uvx --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup \
  --client cursor --client codex --client claude-desktop --client claude-code
```

### 3️⃣ Restart your client and try it

Follow the wizard's restart or new-session instructions. Check that **spotify** appears in your client's tools list, then ask:

> 💬 Use spotify to list my playlists.

✅ Setup checks authorization, tool discovery, and configuration registration. You still need to check the connection **inside your client** and verify playback separately.

📚 More help: [installation, upgrades & recovery](docs/installation.md) · [client acceptance status](docs/client-acceptance.md)

<details>
<summary>📦 What changes after a public PyPI release?</summary>

Once the maintainer publishes this exact version, the separate wheel-install step can be replaced with:

```bash
uvx --python 3.12 --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup
```

That public download flow has not yet been verified. Use the local-wheel steps above for now.

</details>

## 💬 Your first conversation

### 🔎 Search, choose, and preview

Open Spotify on the device you want to use. If it does not appear, play a song and pause it, then list devices again.

Send this first:

> Use spotify to search for Coldplay's Yellow and list devices. Let me choose the track and device, then preview with dry_run=true. Stop after the preview and wait for a new confirmation message. Do not play yet.

### ▶️ Confirm and play

After choosing the track and device and reviewing the preview, send a **new message**:

> I confirm the previewed track and device. Play using the same parameters, then query playback state to verify. If the result is unknown or state is delayed, check state before sending another playback request.

### 🎶 Try a playlist next

> Search for Yellow and Fix You. Show the versions for me to choose, then preview creating a private playlist named Commute. Wait for my confirmation before creating it.

Creating a playlist and adding its songs are separate steps. Once creation returns the real playlist ID, preview adding your chosen songs and confirm that step too.

💡 **A preview does not play audio.** Playback previews check the device, but do not prove that a track exists or is playable. `play_track` starts from the beginning; use `resume_playback` to continue existing playback.

🤝 **Your client manages confirmation.** The server cannot verify the conversation or enforce a new approval message. Ask your client to wait before executing a previewed write, and preview again if the parameters change.

📚 [More recipes: playlists, playback, favorites, and uncertain results](docs/workflows.md)

## 🧰 All 32 tools

| Group | Tools |
|---|---|
| 🔎 Tracks | `search_tracks`, `get_track` |
| 📖 Playlist browsing | `list_playlists`, `get_playlist`, `get_playlist_tracks` |
| ✏️ Playlist editing | `create_playlist`, `update_playlist_details`, `add_playlist_tracks`, `remove_playlist_tracks`, `replace_playlist_tracks`, `reorder_playlist_tracks` |
| 📌 Playlist library | `save_playlist`, `unsave_playlist` |
| 🔊 Playback & devices | `list_devices`, `get_playback_state`, `play_track`, `play_playlist`, `transfer_playback` |
| ⏯️ Player controls | `pause_playback`, `resume_playback`, `next_track`, `previous_track`, `seek_playback`, `set_volume`, `set_shuffle`, `set_repeat` |
| ➕ Queue | `get_queue`, `add_to_queue` |
| ❤️ Saved songs | `get_saved_tracks`, `save_tracks`, `remove_saved_tracks`, `check_saved_tracks` |

### 👀 Preview or run immediately?

| Action | Behavior |
|---|---|
| 📖 Search, browse, and read state | Read-only |
| ⏯️ Pause, resume, next/previous, seek, volume, shuffle, repeat | Run immediately for a clear request, on an explicit device ID |
| ✏️ Other writes | Default to `dry_run=true`; preview, get a new confirmation, then repeat the same parameters with `dry_run=false` |

### 📬 What does a result mean?

| Status | Meaning | Next step |
|---|---|---|
| `submitted` | Spotify accepted the request | Read the affected state to verify it |
| `partial` | Some batches completed before a known failure | Inspect the reported progress and remote state |
| `unknown` | A request may have executed | Check state before deciding whether to retry |

Results use `ok`, `data`, and `error`. A failed batch can still have useful progress in `data`. Writes are not automatically replayed or rolled back, and task progress is not persisted.

<details>
<summary>🔧 Tool limits, playlist behavior & Spotify permissions</summary>

- Track and playlist URIs are `spotify:track:...` and `spotify:playlist:...`; `playlist_id` is the bare ID. Use values returned by reads, not guessed names.
- `create_playlist` defaults to private and creates an empty playlist. Only execution returns its real ID. Preview adding songs separately, then confirm and execute.
- Content-change previews expose `snapshot_id`; pass it as `expected_snapshot_id` at execution. A mismatch requires another read and preview. This is a precheck, not an atomic lock.
- Playlist/favorites pages default to 20, maximum 50. Use `next_offset` until absent. Search retains its original 1–10 result limit.
- Add/remove songs and favorites accept 1–500 URIs, sent sequentially in batches of 100 for playlist items or 40 for library operations. Adding keeps duplicates; URI removal and saving deduplicate and report the mapping.
- Replacement accepts 0–100 tracks in one request and overwrites **all contents**; an empty list clears the playlist. Reordering uses zero-based positions including non-track/unavailable entries.
- `resume_playback` preserves existing context; `play_track` starts a song from the beginning. `transfer_playback` defaults to `play=false`. No audio streaming/preview is provided.
- `save_playlist` saves an existing playlist, and `unsave_playlist` removes it from your library. Neither copies nor deletes its contents.

Business results use `ok/data/error`. A batch failure can return `ok=false` **with progress in data**. `submitted` means the API accepted the request, not verified state. `partial` preserves completed batches; `unknown` identifies a batch that may have executed. Read remote state before deciding to retry. The server does not automatically replay writes, roll back batches, or persist task progress.

See [client workflow recipes and evidence boundaries](docs/workflows.md).

### 🔑 Refresh your permissions

Existing playback-only tokens need additional permissions. Run:

```bash
poetry run spotify-mcp-auth
```

The authorization command requests playback read/currently-playing/modify, playlist read-private/read-collaborative/modify-private/modify-public, and library read/modify permissions. Reuse the same private configuration directory. Tools never open an authorization browser automatically.

Known missing scopes return `insufficient_scope`. An old token without scope metadata is allowed to reach the API; a 403 can also reflect account, application, resource, or device restrictions.

Current endpoints use `/me/playlists`, `/playlists/{id}/items`, and URI-based `/me/library`. Development-mode playlist contents can be restricted to playlists you own or collaborate on; inaccessible content is not an empty playlist. Consult the [migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) and newer [July 2026 changes](https://developer.spotify.com/documentation/web-api/references/changes/july-2026) when checking application access and quotas.

</details>

## 🔐 Credentials & account sharing

📁 By default, private files live outside the repository:

```text
~/.config/spotify-mcp-assistant/
├── .env                  # Spotify app credentials
└── .spotify_token.json   # Cached authorization
```

- 🔒 The wizard keeps credentials and tokens out of client registration entries.
- 🤖 All four clients can share this directory and the same authorization.
- 🔄 Tokens refresh when needed under a cross-process lock. Tool calls never open an authorization browser automatically.
- 📝 Private `.env` values take precedence over inherited shell credentials; missing keys can fall back to the environment.
- 💾 Changed client configurations receive backups. Unrelated settings and existing disabled/approval policies are retained.

To use a separate account or configuration directory:

```bash
uvx --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup \
  --config-dir /ABSOLUTE/PATH/TO/PRIVATE/CONFIG
```

To replace the app credentials or reauthorize a different account:

```bash
uvx --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup --replace-credentials
```

👥 **An account change affects every client sharing that directory.** Keep real `.env` files, tokens, and configuration backups private.

## 🛠️ Troubleshooting

| What you see | What to try |
|---|---|
| 📦 Installation fails | Check uv, the wheel path, and your connection. See [installation help](docs/installation.md). |
| 🤖 Tools do not appear | Restart the client; check disabled entries, project overrides, and client policies. |
| 💻 Claude Code says Pending approval | Approve `spotify` in Claude Code, then check `/mcp`. |
| 🖥️ Claude Desktop has no tools | Fully quit with **Command+Q**, reopen, and check configuration. Logs: `~/Library/Logs/Claude`. |
| 🔑 `auth_required` / `insufficient_scope` | Rerun setup in an interactive terminal with the same private directory to authorize or grant missing permissions. |
| 🚫 `oauth_config_error` / `forbidden` | Check credentials, scopes, account eligibility, and app user access. |
| 🔊 No devices / `device_unavailable` | Open Spotify, play then pause, list devices again, and choose a current device ID. |
| 🔒 `device_restricted` | Select another device. |
| ⏳ `auth_busy` | Wait for another authorization or token refresh to finish, then retry. |
| 🚦 `rate_limited` | Wait according to `retry_after_seconds` when provided. |
| ❓ `playback_result_unknown` / `write_result_unknown` | Read the affected state first; the request may already have reached Spotify. |

Reads retry a Spotify API 401 at most once after refreshing or reusing a newer token. Business writes are not automatically retried. OAuth refresh errors before submission are reported separately.

📚 [Full installation & recovery guide](docs/installation.md)

## 👩‍💻 Manual setup & development

Working on the code? Use Python **≥ 3.10** and Poetry; this release was verified with Python **3.12**. Build a wheel with `poetry build`, or expand the source-based instructions below.

<details>
<summary>📖 Install from source and configure Claude manually</summary>

These instructions register Claude Code at project scope or edit Claude Desktop directly. The wizard above registers all four supported clients at user scope.

### 📦 1. Install the project

#### ✅ Prerequisites

- **Python ≥ 3.10**. This project was verified with Python 3.12.
- **Poetry**. If needed, follow the [Poetry installation guide](https://python-poetry.org/docs/#installation).
- A **Spotify Premium** account for playback.
- Claude Code or Claude Desktop.

After downloading or cloning this repository, enter its directory and run:

```bash
cd spotify-mcp-assistant

# Create a separate environment inside this project
POETRY_VIRTUALENVS_IN_PROJECT=true poetry env use python3.12

# Install the project and dependencies from poetry.lock
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install

# Check the selected Python version
poetry run python --version
```

If `python3.12` is unavailable, pass the absolute path of a supported interpreter to `poetry env use`. Check your system's `python3` version before using it.

**`.venv` is this project's own environment directory.** Dependencies are installed there, rather than in Conda base or another Conda environment. Use `poetry run` without manually activating the environment.

### 🔑 2. Configure Spotify and authorize

#### ① Set up your developer application

Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create or open your own application:

- Obtain its **Client ID** and **Client Secret**.
- Add and save this exact Redirect URI:

```text
http://127.0.0.1:8888/callback
```

The callback address and port are fixed in this project. Keep them unchanged and do not substitute `localhost`. Development-mode application owners need Premium, and the authorizing account must meet the application's user access requirements. See Spotify's [application documentation](https://developer.spotify.com/documentation/web-api/concepts/apps), [redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri), and [development-mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

#### ② Fill in your private configuration

The following commands are for macOS. Run them from the project directory:

```bash
mkdir -p ~/.config/spotify-mcp-assistant

# Preserve an existing configuration
cp -n .env.example ~/.config/spotify-mcp-assistant/.env

nano ~/.config/spotify-mcp-assistant/.env
```

Enter your application credentials:

```dotenv
SPOTIFY_CLIENT_ID=YOUR_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_CLIENT_SECRET
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

In nano, press **Control+O → Enter** to save, then **Control+X** to exit.

Private files live in `~/.config/spotify-mcp-assistant`, outside the repository. Client registration files do not need your Spotify secret.

#### ③ Authorize once

```bash
poetry run spotify-mcp-auth
```

Your browser opens Spotify's authorization page. Confirm your account and grant access. The following terminal message indicates completion:

```text
Authorization completed. Token cache saved.
```

The command creates a new `.spotify_token.json` in the private directory. Tokens refresh when needed. Tool calls never open an authorization browser automatically.

> Authorize using your own configuration. Do not copy real `.env` files or cached tokens from another repository. Port 8888 must be available.

#### 📁 Optional: use a different private directory

`SPOTIFY_CONFIG_DIR` overrides the default directory. It must be an absolute path, optionally starting with `~`; empty and relative values are rejected.

Create and populate `.env` in your chosen directory first, then authorize:

```bash
SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG poetry run spotify-mcp-auth
```

When using a custom directory, pass the same `SPOTIFY_CONFIG_DIR` to the server in each MCP client's configuration.

### 💻 3. Connect Claude Code

From the project directory, run:

```bash
claude mcp add --scope project --transport stdio spotify \
  -- "$(poetry env info --path)/bin/python" \
  -m spotify_mcp_assistant.server
```

This registers the server in the project's `.mcp.json`. The interpreter comes from the Poetry environment; no `PYTHONPATH` is needed.

Start a new Claude Code session:

```bash
claude
```

Approve the project's `spotify` MCP server when prompted. Inside the session, enter:

```text
/mcp
```

Confirm that `spotify` is connected. You can also run `claude mcp get spotify` from the project terminal. If its status is **Pending approval**, enter Claude Code and approve the server first.

**Claude Code starts the server automatically. You do not need a separate server terminal.** See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

For a custom private directory, use this registration command instead. Replace the directory placeholder with your own path:

```bash
claude mcp add --scope project \
  --env SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG \
  --transport stdio spotify \
  -- "$(poetry env info --path)/bin/python" \
  -m spotify_mcp_assistant.server
```

### 🖥️ 4. Connect Claude Desktop

Claude Desktop uses a separate configuration file, so register the server there too.

#### ① Find the interpreter path

From the project terminal, run:

```bash
poetry run python -c "import sys; print(sys.executable)"
```

Copy the complete output. It becomes the `command` value below.

#### ② Edit the desktop configuration

On macOS, use the menu bar: **Claude → Settings → Developer → Edit Config**. The configuration file is located at:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

If you have no other MCP servers, use this complete configuration. Replace the `command` placeholder with the absolute interpreter path copied above:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "/ABSOLUTE/PATH/TO/PROJECT/.venv/bin/python",
      "args": ["-m", "spotify_mcp_assistant.server"]
    }
  }
}
```

If other servers are already configured, add only the `spotify` entry to the existing `mcpServers` object and preserve everything else. Do not overwrite the desktop configuration with the project's `.mcp.json`.

The configuration above uses the default private directory. For a custom directory, add the `env` field from this object to the `spotify` entry:

```json
{
  "env": {
    "SPOTIFY_CONFIG_DIR": "/ABSOLUTE/PATH/TO/PRIVATE/CONFIG"
  }
}
```

Add a comma after the preceding `args` field. Do not include a Client Secret or token in this JSON.

#### ③ Restart and check

Save the file, press **Command+Q to quit Claude Desktop completely**, then reopen it. Start a new chat and check the tools or connectors list for `spotify` and its 32 tools.

Claude Desktop starts the server automatically. You do not need to activate Poetry or run the server manually. See the [official MCP desktop setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

</details>

## 🧪 Development and verification

```bash
poetry check --lock
poetry run pytest tests -v
poetry build
```

The suite verifies all tool groups, schema bounds, default previews, OAuth scopes, pagination, device checks, sequential batching, partial/unknown outcomes, and three simulated MCP workflows. It uses fake data and HTTP responses without real credentials or devices.

Mocked tests do not establish live OAuth, playback, or client confirmation behavior. Follow [the workflow acceptance guide](docs/workflows.md) for real runs and record results separately.

To verify installed stdio discovery from outside the repository:

```bash
poetry run python tests/check_stdio.py \
  --server-python /ABSOLUTE/PATH/TO/INSTALLED/VENV/bin/python \
  --cwd /ABSOLUTE/PATH/OUTSIDE/REPOSITORY
```

This checks both installed entry points and all 32 tools using an empty temporary private configuration; it does not contact Spotify.

To start or inspect entry points directly:

```bash
poetry run spotify-mcp-assistant
poetry run python -m spotify_mcp_assistant.server
poetry run python -m spotify_mcp_assistant.oauth
```
