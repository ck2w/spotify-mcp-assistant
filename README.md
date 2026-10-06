# 🎵 Spotify MCP Assistant

**Your music, playlists, and playback — one conversation away.**

A Python MCP server that lets your AI client search Spotify, build playlists, control playback, manage the queue, and save your favorite songs.

🤖 **Claude Desktop · Claude Code · Codex · Cursor**<br>
🧰 **32 tools** · 🍎 **macOS setup wizard** · 📦 **Version 0.3.0**

The AI client handles the conversation and chooses tools. This project connects those tools to Spotify using **FastMCP over stdio**.

<a id="features"></a>

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

<a id="contents"></a>

## 🧭 Jump to

- [✨ What you can do](#features)
- [🚀 Quick start](#quick-start)
- [💬 Your first conversation](#first-conversation)
- [🎭 Everyday scenarios in Claude](#claude-scenarios)
- [🧰 All 32 tools](#tools)
- [🔐 Credentials & account sharing](#credentials)
- [🛠️ Troubleshooting](#troubleshooting)
- [👩‍💻 Manual setup](#manual-setup)
- [🧪 Development & verification](#development)

<a id="quick-start"></a>

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

<a id="first-conversation"></a>

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

<a id="claude-scenarios"></a>

## 🎭 Everyday scenarios in Claude

Once **spotify** is connected in Claude Desktop or Claude Code, you can describe what you want in plain language. Claude selects the tools and carries the results into the conversation.

The conversations below are **simulated examples of practical use**, not transcripts of live Spotify acceptance. Names, devices, and results are illustrative; Claude should use the actual IDs returned by your account. Tool sequences show a typical path, not a guaranteed model response.

Choose a scenario:

- [🚇 Build a commute playlist](#scenario-commute)
- [💻 Start a focus session](#scenario-focus)
- [❤️ Save the song playing now](#scenario-save-song)
- [🎉 Add a friend's song to the queue](#scenario-party)
- [🧹 Tidy an existing playlist](#scenario-tidy)
- [📌 Keep a playlist in your library](#scenario-library)

<a id="scenario-commute"></a>

### 🚇 1. Build a commute playlist together

**When it helps:** You have a few favorite artists and want Claude to handle searching, version selection, and playlist setup.

> **You:** Use spotify to help me build a private playlist called Morning Commute. Search for Yellow by Coldplay, Dreams by Fleetwood Mac, and Here Comes the Sun by The Beatles. Show the versions first, and wait for me to choose.
>
> **Claude:** Here are the matching versions from Spotify. Which would you like to use?
>
> **You:** Use the studio versions I selected. Preview creating the private playlist, then wait.
>
> **Claude:** Preview: create an empty private playlist named Morning Commute. No changes have been made.
>
> **You:** Confirm creation.
>
> **Claude:** Spotify accepted creation and returned the playlist ID. Here is a separate preview of adding your three selected tracks in order. Please confirm that step.
>
> **You:** Confirm adding those tracks.
>
> **Claude:** I will execute that preview, then read the playlist and its tracks to check the result.

🧰 **Typical tools:** `search_tracks` → `create_playlist` → `add_playlist_tracks` → `get_playlist` / `get_playlist_tracks`.

💡 Claude can suggest songs from your description and search for them. This MCP does not provide audio analysis or Spotify's personalized recommendation engine.

<a id="scenario-focus"></a>

### 💻 2. Start a focus session without opening Spotify's menus

**When it helps:** You already have a study or coding playlist and want to choose a device, start it, and adjust playback from the chat.

> **You:** Use spotify to find my Deep Focus playlist and list available devices. Let me choose both, then preview playback. Do not start yet.
>
> **Claude:** I found these playlists and devices. Which playlist and device should I use?
>
> **You:** Use the playlist I selected and my MacBook. Show the playback preview.
>
> **Claude:** Preview: play that playlist on the selected MacBook device. Shall I execute it?
>
> **You:** Confirm. Start it and check playback state.
>
> **Claude:** I will send the request and check whether the selected playlist is playing on that device.
>
> **You:** On that same device, set volume to 25% and turn shuffle off.

🧰 **Typical tools:** `list_playlists` → `list_devices` → `play_playlist` → `get_playback_state` → `set_volume` / `set_shuffle`.

⏯️ Volume and shuffle are direct controls; a clear request runs immediately on the selected device. You can also say “pause” or “resume on that device.” This flow does not schedule a focus timer or automatically stop playback later.

<a id="scenario-save-song"></a>

### ❤️ 3. Save the song you are hearing right now

**When it helps:** A song catches your attention, and you want to identify it and add it to your saved songs.

> **You:** Use spotify to tell me what's playing now and whether I've already saved it. If it isn't saved, preview saving it and wait for confirmation.
>
> **Claude:** The playback result identifies this track, and the library check says it isn't saved. Here is the save preview.
>
> **You:** Confirm saving that exact track, then check its saved state.
>
> **Claude:** I will save the previewed track URI and check it again.

🧰 **Typical tools:** `get_playback_state` → `check_saved_tracks` → `save_tracks` → `check_saved_tracks`.

💡 If nothing is playing, or the current item is not a supported track, Claude should explain that rather than guess. If the song changes before confirmation, save only the track you previewed or ask for a new preview.

<a id="scenario-party"></a>

### 🎉 4. Add a friend's request without interrupting the current song

**When it helps:** Someone requests a song during a gathering, and you want to queue the right version on the right device.

> **You:** Use spotify to search for Dancing Queen by ABBA. Show the versions, current queue, and devices. I want to queue it without replacing the current playback.
>
> **Claude:** Here are the matching tracks, queue, and devices. Which track and device should I use?
>
> **You:** Use the version and living-room device I selected. Preview adding it to the queue.
>
> **Claude:** Preview: add the selected track to the queue on that device. Waiting for confirmation.
>
> **You:** Confirm, then show the queue again.

🧰 **Typical tools:** `search_tracks` → `get_queue` / `list_devices` → `add_to_queue` → `get_queue`.

💡 The queue changes as music plays. If the write result is uncertain, inspect the queue before retrying; replaying the request could add the song twice.

<a id="scenario-tidy"></a>

### 🧹 5. Review and tidy an existing playlist

**When it helps:** A playlist has grown messy, and you want to understand its contents before changing the order.

> **You:** Use spotify to find my Road Trip playlist. Let me select it, then read all its track pages. Show the order and repeated track URIs. Don't change anything yet.
>
> **Claude:** Here is the full order. These exact track URIs appear more than once; different versions may have different URIs.
>
> **You:** Move the final track to the beginning. Preview the reorder and wait.
>
> **Claude:** Here is the reorder preview with the current playlist snapshot.
>
> **You:** Confirm that reorder. Then read the playlist again and show the new order.

🧰 **Typical tools:** `list_playlists` → `get_playlist` / `get_playlist_tracks` → `reorder_playlist_tracks` → `get_playlist_tracks`.

💡 Claude compares the returned data in the conversation; there is no separate cleanup tool. A changed snapshot requires a fresh read and preview. Removing a track by URI can remove all its occurrences, so “delete just one duplicate” must not be treated as a simple URI removal.

<a id="scenario-library"></a>

### 📌 6. Keep a shared playlist in your library

**When it helps:** You have a playlist ID or Spotify playlist URI and want to save it for easy access later.

> **You:** Use spotify to inspect this playlist: `spotify:playlist:<PLAYLIST_ID>`. Show its name and whether I can access its contents. Preview saving it to my library, but don't change it yet.
>
> **Claude:** Here is the playlist information and the save preview. Saving adds the existing playlist to your library; it does not copy its tracks.
>
> **You:** Confirm saving that playlist, then check my playlist list for it.

🧰 **Typical tools:** `get_playlist` → `save_playlist` → `list_playlists` (follow pagination as needed).

💡 Replace `<PLAYLIST_ID>` with a real ID. `unsave_playlist` removes the library entry; it does not delete the playlist or clear its songs. Spotify app access restrictions can limit which playlist contents are readable.

📚 [Detailed workflow rules and how to handle partial or unknown results](docs/workflows.md)

<a id="tools"></a>

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

<a id="credentials"></a>

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

<a id="troubleshooting"></a>

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

<a id="manual-setup"></a>

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

<a id="development"></a>

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
