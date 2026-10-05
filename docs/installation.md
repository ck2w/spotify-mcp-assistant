# macOS installation and recovery

Use the same Python stdio MCP with Claude Desktop, Claude Code, Codex or Cursor. The setup wizard is macOS-only; the existing manual server entry points remain available. No Node.js, npm, web service or separate Agent is required.

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). For this unpublished 0.3.0 release, get the wheel from the maintainer. Maintainers can produce it with `poetry build`.

```bash
uv tool install --python 3.12 /ABSOLUTE/PATH/spotify_mcp_assistant-0.3.0-py3-none-any.whl
uvx --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup
```

uv prepares Python and an isolated persistent tool environment. The wizard locates that installation, verifies the package version and registers absolute paths. GUI apps do not need uv or Python on their PATH, and clearing uv's temporary cache does not remove the tool environment. Do not manually delete its Python installation or environment.

The future public bootstrap command is:

```bash
uvx --python 3.12 --from spotify-mcp-assistant==0.3.0 spotify-mcp-setup
```

Use it only after the maintainer publishes this release. PyPI publishing and the public download path have not been performed here.

## First authorization

1. Select one or more clients, or repeat `--client cursor`, `--client codex`, `--client claude-desktop`, `--client claude-code`.
2. Create your own app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Register exactly `http://127.0.0.1:8888/callback`. Paste the Client ID and enter the Client Secret at the hidden prompt.
3. Grant the requested Spotify permissions in the browser. Setup performs a read-only device request and does not start playback or change playlists.
4. Setup starts the installed MCP outside your checkout and checks the exact 32 tools, then backs up and merges client configurations.
5. Follow the printed restart/new-session instructions, check the client tools list and try “Use spotify to list my playlists.”

Spotify application access and playback eligibility remain separate. Playback requires Premium. If using a developer's shared app, your account must be allowlisted; logging in does not by itself establish API access. See [Spotify quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

## Private data and clients

Default private directory: `~/.config/spotify-mcp-assistant`. Its `.env` and `.spotify_token.json` are outside the source checkout. Private files and backups use permission 0600, the private directory 0700. Client entries contain only the launch command and the private-directory path. Tokens refresh under a cross-process file lock.

`--config-dir /ABSOLUTE/PATH` overrides `SPOTIFY_CONFIG_DIR`; otherwise the default applies. `~` is expanded; empty or relative paths are rejected. Setup uses the chosen directory's credentials. The runtime reads private-file values before fallback environment values, preventing old shell credentials from overriding the selected application.

| Client | User configuration |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `~/.claude.json` |
| Codex | `~/.codex/config.toml`, or an existing absolute `CODEX_HOME` directory |
| Cursor | `~/.cursor/mcp.json` |

Only the `spotify` server is updated; unrelated settings are retained. Existing disabled flags and approval settings remain in effect. Enable a disabled entry yourself. A project's same-name server can override the user entry; check project-level settings if you see an old launch command. A different same-name service requires an explicit replace choice. Setup does not automatically edit symlinked configuration files or parse commented JSON.

## Rerun, repair and upgrade

Repeat setup to add a client or repair its entry. A valid authorization is reused. Equivalent client entries produce no write and no new backup. A changed entry is backed up using a unique `.backup-…` suffix alongside the configuration.

To change application or account, run setup with `--replace-credentials`; this affects every client sharing the private directory. Authorization and its read-only check must pass before the new credentials and token replace the old pair. If saving fails, setup attempts to restore the previous files; private `.backup-…` files are retained for recovery.

Upgrades are explicit. Install the maintainer's new wheel or published exact version with uv, then run that version's setup and restart clients. Daily MCP startup does not automatically fetch releases. An executable owned by a different installer is not force-overwritten.

If one client fails, other successful configurations remain. Rerun using `--client` for the failed client. If restoring a backup manually, quit settings editors, copy the exact backup over its original file, then restart the client. Backups can contain other MCP credentials; keep them private.

## Troubleshooting

| Problem | Action |
|---|---|
| uv missing or installation failed | Install uv; check connection and supplied wheel/version. Check for a conflicting executable from pipx or another installer. |
| Noninteractive terminal | Run setup in a normal interactive terminal for client choices and authorization prompts. |
| Invalid JSON/TOML or symlink | Repair the file or configure its resolved target manually; setup does not overwrite it. |
| Configuration changed during setup | Close other settings editors and rerun. Setup's pre-write check cannot atomically lock another application's saves. |
| Authorization failed/timed out | Check Client ID/Secret, app callback, consent and port 8888; retry. |
| `forbidden` | Check app user access, permissions and account requirements. |
| `rate_limited` / network failure | Wait or fix the connection; rerun without discarding the prior authorization. |
| `auth_busy` | Another process holds the token lock; wait for authorization/refresh to finish. |
| No devices | Open Spotify and play/pause something. An empty device list does not mean setup failed. |
| MCP discovery failed | Repair the persistent uv tool installation and rerun setup. |
| Tools still absent | Follow restart instructions; check disabled entries, project overrides and client policy. |

Exit codes: 0 = authorization, discovery and all selected configurations completed; 1 = failed/skipped stage or client; 2 = invalid invocation, required interaction missing or cancellation. “Client-in-app acceptance: NOT RUN” means you still need to verify inside the app.

Tool calls do not open an authorization browser. Run setup or the existing `spotify-mcp-auth` command explicitly if authorization expires.
