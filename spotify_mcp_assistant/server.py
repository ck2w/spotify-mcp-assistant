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
            "Search for tracks and list devices before playback. "
            "Preview with dry_run=True, then wait for a new user message "
            "confirming the exact song and device before dry_run=False. "
            "An initial request to play is not confirmation of a later preview. "
            "play_track restarts a track; it does not resume its saved position. "
            "Verify playback using get_playback_state. "
            "If playback_result_unknown occurs, check playback state "
            "before attempting playback again."
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
