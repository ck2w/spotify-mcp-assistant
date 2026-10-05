# Client workflows and verification

The server provides tools; Claude Code, Claude Desktop, or another compatible MCP client performs the conversation and selects calls. These recipes do not install a separate Agent or web app.

## 1. Create and verify a playlist

First message:

> Search for Coldplay's Yellow and Fix You. Show versions for me to choose. Preview a private playlist named Commute. Stop and wait for my confirmation before creating it.

After selecting and seeing the preview, send a new confirmation message. The executed `create_playlist` returns a real `playlist_id`; its preview does not. Next preview `add_playlist_tracks` with the chosen track URIs and that ID, then wait for a new confirmation. Execute the same parameters with the preview snapshot as `expected_snapshot_id`. Read `get_playlist` and all `get_playlist_tracks` pages to check the name, URIs, order, and duplicate occurrences.

A successful HTTP response means submitted. It does not establish the entire workflow succeeded. Never create another playlist solely because an earlier creation timed out. Read `list_playlists` first; names are not unique, so an uncertain result may remain uncertain.

## 2. Play, pause, resume, and queue

> List devices and let me select one. Preview playing my selected playlist on that device. Stop after preview and wait for a new confirmation.

After confirmation execute `play_playlist` with the same URI/device. Read `get_playback_state` and check `context_uri`, `device.device_id`, and `is_playing`. A missing or delayed observation is not verified success.

A clear request to pause or resume calls `pause_playback` or `resume_playback` directly. Resume does not replace context or restart a selected song; `play_track` does restart a song. Next/previous, seek, volume, shuffle, and repeat also execute directly on an explicit device ID.

To add a song, preview `add_to_queue`, wait for a new confirmation, execute, then inspect `get_queue`. The queue is dynamic; an observation may not prove whether a specific prior addition happened. Never blindly replay an unknown queue addition.

## 3. Save and remove songs

Check `check_saved_tracks` first. Preview `save_tracks` for chosen URIs; after a new user confirmation execute and check saved state. Preview `remove_saved_tracks` before removing favorites, confirm, execute, and check again.

`save_playlist` adds an existing playlist to your library. `unsave_playlist` removes that library entry; it does not delete the playlist or clear its contents.

## 4. Partial or unknown writes

Batch results report `normalized_uris` and `input_indices`, mapping deduplicated inputs back to the original list. Progress ranges use normalized indices with an exclusive upper bound:

```json
{
  "ok": false,
  "data": {
    "status": "unknown",
    "submitted_count": 100,
    "submitted_ranges": [[0, 100]],
    "unknown_range": [100, 200],
    "not_attempted_ranges": [[200, 201]]
  },
  "error": {"code": "write_result_unknown"}
}
```

This abbreviated example is **simulated**, not a live Spotify response. The first batch received a successful response, the second may have executed, and the third was not attempted. Query remote state before deciding the next step. Repeated songs and concurrent changes can prevent a definitive match. There is no automatic rollback, atomic multi-request transaction, or persisted server recovery.

For a known rejection after a completed batch, status is `partial` and `failed_range` identifies the rejected batch. A precheck failure leaves the current and remaining ranges unattempted. `check_saved_tracks` preserves known values and labels the remaining inputs `unqueried_uris`; they are not false.

## Evidence and live acceptance

Automated `tests/test_workflows.py` runs the real MCP adapters and domain code against fake HTTP data. It verifies composition, schema, and result propagation. It does **not** establish that a model resolved ambiguity or waited for user approval.

Installed stdio discovery is checked offline with `tests/check_stdio.py`. Live Spotify OAuth, real playback, and client behavior require a separate run with an eligible account and user's confirmation.

Current status: simulated workflows verified; live Spotify/client workflows **not run for this release**. Update this statement only after an actual acceptance run.

Use this record format for each real run:

| Field | Record |
|---|---|
| Date and client/version | Actual date, client, and version |
| Scenario | Playlist / playback / favorites |
| Expected behavior | Target selection, preview, confirmation, writes, reads |
| Observed behavior | What actually happened; include uncertainty |
| Confirmation followed? | Yes / no / not applicable |
| Result verified? | Yes / no / unknown, with observation |
| Duplicate write? | Yes / no / cannot determine |
| Evidence | Sanitized messages/tool results, with private identifiers removed |

Do not commit credentials, authorization codes, tokens, real device IDs, or unnecessary account data. Do not report a success rate until scenarios have actually been run.
