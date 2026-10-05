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


    @server.tool(annotations={"readOnlyHint": True})
    def list_devices() -> DevicesResult:
        """List Spotify devices. Use a non-null device_id from an
        unrestricted device as the device_id argument to play_track.
        If no devices are available, open Spotify, play then pause,
        and call this tool again.
        """
        try:
            devices = spotify_client.list_devices()
            return DevicesResult(ok=True, data=devices)
        except SpotifyError as error:
            return DevicesResult(ok=False, error=error.error)


    @server.tool(annotations={"readOnlyHint": True})
    def get_playback_state() -> PlaybackResult:
        """Read the current song, device, playback status and progress.
        Use after play_track to verify the requested song is playing.
        has_playback=False means no playback state is available.
        """
        try:
            state = spotify_client.get_playback_state()
            return PlaybackResult(ok=True, data=state)
        except SpotifyError as error:
            return PlaybackResult(ok=False, error=error.error)


    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def play_track(
        track_uri: Annotated[
            str,
            Field(
                pattern=r"^spotify:track:[A-Za-z0-9]{22}$",
                description="A track_uri returned by search_tracks",
            ),
        ],
        device_id: Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1),
            Field(description="A non-null device_id returned by list_devices"),
        ],
        dry_run: Annotated[
            bool,
            Field(description="Preview only unless explicitly set to false"),
        ] = True,
    ) -> PlayResult:
        """Preview or start playback on a specific Spotify device.
        First call with dry_run=True, then stop and wait for a new user
        message confirming that preview's song and device. Only then
        use the same parameters with dry_run=False. An initial request
        to play does not count as confirmation of a later preview.
        This tool starts the track from the beginning, not its saved position.
        After submission, call get_playback_state to verify playback.
        If playback_result_unknown occurs, check state before retrying.
        """
        try:
            result = spotify_client.play_track(track_uri, device_id, dry_run)
            return PlayResult(ok=True, data=result)
        except SpotifyError as error:
            return PlayResult(ok=False, error=error.error)


    from spotify_mcp_assistant.tools import catalog, playlists, library
    catalog.register_tools(server)
    playlists.register_tools(server)
    library.register_tools(server)
    return server


mcp = create_server()

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
