from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StringConstraints

from spotify_mcp_assistant import spotify_client
from spotify_mcp_assistant.models import DevicesResult, PlaybackResult, PlayResult, SearchResult
from spotify_mcp_assistant.spotify_client import SpotifyError

def create_server() -> FastMCP:
    server = FastMCP(
        "Spotify Playback Assistant",
        instructions=(
            "Use these Spotify tools for clear user requests. Resolve ambiguous tracks and devices with the user. "
            "Playlist and library mutations, queue additions, transfers, and starting track/playlist playback "
            "default to dry_run=True. Show the preview, then wait for a NEW user message confirming "
            "the exact parameters before dry_run=False. Changed parameters require another preview. "
            "Pause/resume, next/previous, seek, volume, shuffle and repeat execute immediately without dry_run. "
            "Confirmation is enforced by the client conversation, not by this server. "
            "play_track restarts a track; resume_playback preserves the existing context. "
            "Use real playlist_id from executed create_playlist; creation preview has no ID. "
            "For content changes pass the preview snapshot_id as expected_snapshot_id. "
            "Read list pages using next_offset; do not claim a partial page is the whole library. "
            "Submitted means a successful API response, not verified state. Read playlist contents, "
            "check_saved_tracks or get_playback_state to verify. "
            "On partial/unknown writes preserve progress, inspect state before retrying, "
            "and never blindly repeat creation, queue addition or playback. "
            "Replacement overwrites all playlist contents; empty replacement clears it. "
            "unsave_playlist removes a library entry, not the playlist itself."
        ),
    )


    from spotify_mcp_assistant.tools import catalog, playlists, library, playback
    catalog.register_tools(server)
    playlists.register_tools(server)
    library.register_tools(server)
    playback.register_tools(server)
    return server


mcp = create_server()

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
