# 🎵 Spotify MCP Assistant

Find and play music through conversations in Claude Code or Claude Desktop:

**Search → Choose a track and device → Preview → Confirm → Play → Verify**

An independent Python project built with **FastMCP over stdio**. Version 1 exposes four tools, without recommendations, similar-track discovery, or a custom chat UI.

## 🧭 Start here

1. [Install the project](#-1-install-the-project)
2. [Configure Spotify and authorize](#-2-configure-spotify-and-authorize)
3. Connect [Claude Code](#-3-connect-claude-code) or [Claude Desktop](#-4-connect-claude-desktop)
4. [Start using the assistant](#-5-start-using-the-assistant)

Both clients can use the same private configuration directory and authorization.

## 📦 1. Install the project

### Prerequisites

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

## 🔑 2. Configure Spotify and authorize

### ① Set up your developer application

Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create or open your own application:

- Obtain its **Client ID** and **Client Secret**.
- Add and save this exact Redirect URI:

```text
http://127.0.0.1:8888/callback
```

The callback address and port are fixed in this project. Keep them unchanged and do not substitute `localhost`. Development-mode application owners need Premium, and the authorizing account must meet the application's user access requirements. See Spotify's [application documentation](https://developer.spotify.com/documentation/web-api/concepts/apps), [redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri), and [development-mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

### ② Fill in your private configuration

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

### ③ Authorize once

```bash
poetry run spotify-mcp-auth
```

Your browser opens Spotify's authorization page. Confirm your account and grant access. The following terminal message indicates completion:

```text
Authorization completed. Token cache saved.
```

The command creates a new `.spotify_token.json` in the private directory. Tokens refresh when needed. Tool calls never open an authorization browser automatically.

> Authorize using your own configuration. Do not copy real `.env` files or cached tokens from another repository. Port 8888 must be available.

### Optional: use a different private directory

`SPOTIFY_CONFIG_DIR` overrides the default directory. It must be an absolute path, optionally starting with `~`; empty and relative values are rejected.

Create and populate `.env` in your chosen directory first, then authorize:

```bash
SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG poetry run spotify-mcp-auth
```

When using a custom directory, pass the same `SPOTIFY_CONFIG_DIR` to the server in each MCP client's configuration.

## 💻 3. Connect Claude Code

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

## 🖥️ 4. Connect Claude Desktop

Claude Desktop uses a separate configuration file, so register the server there too.

### ① Find the interpreter path

From the project terminal, run:

```bash
poetry run python -c "import sys; print(sys.executable)"
```

Copy the complete output. It becomes the `command` value below.

### ② Edit the desktop configuration

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

### ③ Restart and check

Save the file, press **Command+Q to quit Claude Desktop completely**, then reopen it. Start a new chat and check the tools or connectors list for `spotify` and its four tools.

Claude Desktop starts the server automatically. You do not need to activate Poetry or run the server manually. See the [official MCP desktop setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

## ▶️ 5. Start using the assistant

Open Spotify so the target device is discoverable. If no devices appear, try playing a track and then pausing it.

**First message: search and preview**

> Use spotify to search for Coldplay's Yellow and list devices. Let me choose the track and device, then preview with dry_run=true. Stop after the preview and wait for a new confirmation message. Do not play yet.

**After selecting a track and device and seeing the preview, send a new message:**

> I confirm the previewed track and device. Play using the same parameters, then query playback state to verify. If the result is unknown or state is delayed, check state first rather than sending another playback request.

Keep these behaviors in mind:

- **Preview is not audio playback.** It checks the device without sending a playback PUT. It does not verify track existence or playability.
- **Confirmation is an assistant instruction.** Version 1 has no server approval token; a client can still call `dry_run=False` directly.
- **Playback starts from the beginning.** It does not resume saved progress.
- **`submitted` does not mean verified.** Query state and check that the track URI and device ID match and `is_playing=True`.
- Changing the track or device requires another preview and confirmation. Do not automatically switch devices or repeat playback requests.

## 🧰 Four tools

| Tool | Purpose |
|---|---|
| `search_tracks(query, limit=5)` | Find tracks by title, artist, or Spotify query syntax; return names, artists, URIs, and links. Limit: 1–10. |
| `list_devices()` | List devices and active/restricted flags. Null IDs and restricted devices cannot be playback targets. |
| `play_track(track_uri, device_id, dry_run=True)` | Preview by default; explicitly pass `False` to play on the selected device. |
| `get_playback_state()` | Read the track, device, playing state, and progress for verification. |

Business results use `ok/data/error`. Business failures return `ok=False`; input schema failures are MCP tool errors.

## 🛠️ Troubleshooting

| Symptom | Next action |
|---|---|
| Claude Code shows Pending approval | Start `claude` in the project directory, approve `spotify`, then check `/mcp`. |
| Claude Desktop does not show tools | Check the JSON and absolute interpreter path, then fully quit and restart. macOS logs are in `~/Library/Logs/Claude`. |
| `auth_required` | Run `poetry run spotify-mcp-auth` from the project directory, using the same private directory as the client. |
| `oauth_config_error` / `forbidden` | Check credentials, granted scopes, account eligibility, and application user access. |
| No devices / `device_unavailable` | Open Spotify, play then pause, list devices again, and select a current ID. |
| `device_restricted` | Ask the user to select another device. |
| `rate_limited` | Wait according to `retry_after_seconds` when provided. |
| `playback_result_unknown` | Read state first. The request may have reached Spotify; do not immediately replay. |

Reads retry an API 401 at most once after refreshing the token. Playback writes are not automatically retried. Malformed token files, some configuration failures, and authorization timeouts retain the original authorization module's failure behavior.

## 🧪 Development and verification

```bash
poetry check --lock
poetry run pytest tests -v
poetry build
```

The suite contains nine reused cases and one configuration-path test. It uses fake data and mocks, without real credentials or playback devices. Separate checks verified standalone installation, startup outside the repository, and both stdio entry points.

Mocked tests do not establish live OAuth or playback success. After configuring and authorizing, use the preview, confirmation, and verification workflow above for real acceptance testing.

To start or inspect entry points directly:

```bash
poetry run spotify-mcp-assistant
poetry run python -m spotify_mcp_assistant.server
poetry run python -m spotify_mcp_assistant.oauth
```
