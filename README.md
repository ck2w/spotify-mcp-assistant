# Spotify MCP Assistant

A music assistant for focused work, used through an existing MCP client's chat. Specify a song or artist, choose a track and device, preview the action, then confirm playback and verify the result.

This independent Python package uses FastMCP over stdio. It provides four tools and does not include recommendations or a chat UI.

## Tools

| Tool | Purpose |
|---|---|
| `search_tracks(query, limit=5)` | Find tracks by title, artist or Spotify search query; return names, artists, URIs and links. Limit: 1–10. |
| `list_devices()` | Read devices, including nullable IDs and active/restricted flags. |
| `play_track(track_uri, device_id, dry_run=True)` | Preview by default; start the selected track and device when `dry_run=False`. |
| `get_playback_state()` | Read the current track, device, playing status and progress. |

Tools return `ok`, `data` and `error` fields. Business failures use `ok=False`; input schema failures are MCP tool errors. Errors include a code, message, next action and retry information.

## Install with Poetry

Requirements: Python 3.10 or later and Poetry. Python 3.12 is used for this migration. From the project directory:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry env use python3.12
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install
poetry run python --version
```

If your interpreter has another name, pass its absolute path to `poetry env use`. Some machines have an older system `python3`; check its version first. Poetry installs dependencies in the project's `.venv`, rather than in Conda base or another environment. Use `poetry run` without activating it. Commit `poetry.lock`, not `.venv`.

## Configure and authorize

Use your own Spotify developer application and an account with access to it. Playback requires Premium and a visible, controllable Spotify device. Application access and scope restrictions can produce `forbidden` errors.

The private directory defaults to `~/.config/spotify-mcp-assistant`. `SPOTIFY_CONFIG_DIR` can override it with an absolute path, optionally beginning with `~`; empty and relative values are rejected. It is independent of the client's working directory.

From the project directory, create your own configuration:

```bash
mkdir -p ~/.config/spotify-mcp-assistant
cp .env.example ~/.config/spotify-mcp-assistant/.env
```

Fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in that private file. Register the exact redirect URI `http://127.0.0.1:8888/callback` in Spotify application settings. The callback address and port are fixed; ensure port 8888 is available, then run:

```bash
poetry run spotify-mcp-auth
```

This command opens authorization and creates a new `.spotify_token.json` in the private directory. It requests only `user-read-playback-state` and `user-modify-playback-state`. Cached tokens refresh when needed. Tool calls never open an authorization browser; missing or revoked authorization asks you to run the command yourself.

For another directory, create and populate its `.env` first, then use the same setting during authorization and MCP startup:

```bash
SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG poetry run spotify-mcp-auth
```

Do not copy credentials or cached tokens from another repository. Configuration, tokens and real client registrations must not be committed.

## Connect an MCP client

```bash
poetry run spotify-mcp-assistant
```

For clients supporting `.mcp.json`, adapt `.mcp.json.example` using the absolute path to **this project's `.venv/bin/python`**. No `PYTHONPATH` is needed:

```json
{
  "mcpServers": {
    "spotify": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/PROJECT/.venv/bin/python",
      "args": ["-m", "spotify_mcp_assistant.server"]
    }
  }
}
```

This snippet uses the default private directory. The supplied example file includes an optional `env.SPOTIFY_CONFIG_DIR`: replace the placeholder with your private directory, or remove `env` to use the default. Adapt the registration structure to your client's format while keeping the command, arguments and environment setting.

Module entry points are also available:

```bash
poetry run python -m spotify_mcp_assistant.server
poetry run python -m spotify_mcp_assistant.oauth
```

## Conversation workflow

1. Specify a song or artist. The assistant searches tracks and lists devices. Choose explicitly when results or devices are ambiguous; null IDs and restricted devices cannot be playback targets.
2. The assistant calls `play_track` with `dry_run=True` and shows the song and device. Preview reads device availability but sends no playback PUT. It validates URI format and device eligibility, not song existence or playability; it is not audio playback.
3. Send a **new message after preview** confirming the exact song and device. The initial request to play does not count. Changing either selection requires another preview and confirmation.
4. The assistant calls `dry_run=False` with the same IDs, then reads state. Report verified playback only when track URI and device match and `is_playing=True`.

Confirmation is an assistant instruction, not a server approval token. A client can call `dry_run=False` directly; MCP annotations do not enforce approval. `play_track` starts from the beginning, rather than resuming saved progress. `submitted` means the request was accepted, not that playback was verified. If state is delayed or unavailable, query state again instead of automatically replaying.

## Troubleshooting

| Result | Next action |
|---|---|
| `auth_required` | Run `poetry run spotify-mcp-auth` using the same private directory. |
| `oauth_config_error` / `forbidden` | Check credentials, application access, granted scopes and account requirements. |
| No devices / `device_unavailable` | Open Spotify, play then pause, list devices again and select a current ID. |
| `device_restricted` | Select another device; do not silently change the user's target. |
| `rate_limited` | Wait according to `retry_after_seconds` when present. |
| `playback_result_unknown` | Read state before attempting playback again; the write may have reached Spotify. |

Reads retry API 401 at most once after forced refresh. Writes are not automatically retried. Malformed token files, some configuration failures and authorization port/timeout errors retain the original authorization module's failure behavior.

## Development and verification

```bash
poetry check --lock
poetry run pytest tests -v
poetry build
```

The suite contains nine migrated cases and one configuration-directory test. Tests use fake data and mocked Spotify requests, without credentials, browsers or real playback. Separate installation checks verify stdio module and console startup outside the repository.

These checks do not establish live OAuth or playback success. After you configure and authorize your own application, follow the conversation workflow for a real demonstration and keep device and credential details out of shared transcripts.
