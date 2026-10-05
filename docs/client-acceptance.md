# Client acceptance for 0.3.0

Record actual client evidence separately from configuration generation and offline MCP discovery. Never put credentials, token responses, device IDs or private client configurations in this document.

| Client | Real client connection | Read-only tool call | Confirmation workflow |
|---|---|---|---|
| Claude Desktop | Not run | Not run | Not run |
| Claude Code | Not run | Not run | Not run |
| Codex | Not run | Not run | Not run |
| Cursor | Not run | Not run | Not run |

Real Spotify login and account/device eligibility have not been verified for this release. Intel macOS has not been tested. The setup wizard's success does not change these statuses automatically.

Local evidence on 2026-10-05: 156 regression tests passed; wheel installation in isolated uv tool directories on Apple Silicon macOS succeeded; installed stdio discovered exactly 32 tools from outside the repository with a minimal PATH. Simulated four-client first setup/rerun preserved other settings and disabled policies, reused private authorization, rejected external configuration changes and retained old private files after a failed account switch. Spotify responses and browser authorization were simulated for that flow.

For a real run, record date, macOS/CPU and client version, installed package version, configuration registration, restart/new session, exact tool discovery and a read-only request such as list_playlists. Mark skipped or failed steps accurately. Confirmation/playback checks are optional separate acceptance with the user's explicit intent.

Automated regression tests and isolated wheel/discovery checks cover local software behavior. Simulated authorization verifies the setup flow, not Spotify's live consent or a model's conversation behavior. The public PyPI bootstrap cannot be accepted until the release is actually published and downloaded in a clean environment.
