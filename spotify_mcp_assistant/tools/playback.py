from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from spotify_mcp_assistant import playback, spotify_client
from spotify_mcp_assistant.models import (
    BusinessResult,
    DeviceID,
    DevicesResult,
    MutationData,
    PlaybackResult,
    PlaylistURI,
    PlayResult,
    QueueData,
    TrackURI,
)
from spotify_mcp_assistant.spotify_client import SpotifyError
from spotify_mcp_assistant.tools import result


def register_tools(server):
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

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def pause_playback(device_id: DeviceID) -> BusinessResult[MutationData]:
        """Execute pause_playback immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(BusinessResult[MutationData], playback.pause_playback, device_id)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def resume_playback(device_id: DeviceID) -> BusinessResult[MutationData]:
        """Execute resume_playback immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Resume saved progress without replacing the playback context. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(BusinessResult[MutationData], playback.resume_playback, device_id)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def next_track(device_id: DeviceID) -> BusinessResult[MutationData]:
        """Execute next_track immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(BusinessResult[MutationData], playback.next_track, device_id)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def previous_track(device_id: DeviceID) -> BusinessResult[MutationData]:
        """Execute previous_track immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(BusinessResult[MutationData], playback.previous_track, device_id)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def seek_playback(
        position_ms: Annotated[int, Field(ge=0)], device_id: DeviceID
    ) -> BusinessResult[MutationData]:
        """Execute seek_playback immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(
            BusinessResult[MutationData], playback.seek_playback, position_ms, device_id
        )

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def set_volume(
        volume_percent: Annotated[int, Field(ge=0, le=100)], device_id: DeviceID
    ) -> BusinessResult[MutationData]:
        """Execute set_volume immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(
            BusinessResult[MutationData], playback.set_volume, volume_percent, device_id
        )

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def set_shuffle(state: bool, device_id: DeviceID) -> BusinessResult[MutationData]:
        """Execute set_shuffle immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(
            BusinessResult[MutationData], playback.set_shuffle, state, device_id
        )

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def set_repeat(
        state: Literal["off", "context", "track"], device_id: DeviceID
    ) -> BusinessResult[MutationData]:
        """Execute set_repeat immediately on the explicitly selected device; no preview or extra confirmation. Only use for a clear user request. Verify with get_playback_state. Unknown writes must not be blindly retried."""
        return result(
            BusinessResult[MutationData], playback.set_repeat, state, device_id
        )

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def play_playlist(
        playlist_uri: PlaylistURI, device_id: DeviceID, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview starting a playlist context on the chosen device. Wait for a new user confirmation before dry_run=false with identical parameters. Verify context_uri/device/is_playing via get_playback_state."""
        return result(
            BusinessResult[MutationData],
            playback.play_playlist,
            playlist_uri,
            device_id,
            dry_run,
        )

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def transfer_playback(
        device_id: DeviceID, play: bool = False, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview moving playback to one chosen device. play=false does not request starting playback. Wait for new user confirmation before execution; verify target with get_playback_state."""
        return result(
            BusinessResult[MutationData],
            playback.transfer_playback,
            device_id,
            play,
            dry_run,
        )

    @server.tool(annotations={"readOnlyHint": True})
    def get_queue() -> BusinessResult[QueueData]:
        """Read the current user's queue (no device parameter or pagination). This is a dynamic observation and may not prove a previous add succeeded."""
        return result(BusinessResult[QueueData], playback.get_queue)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def add_to_queue(
        track_uri: TrackURI, device_id: DeviceID, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview adding one song to the chosen device queue. Confirm in a new user message before execution. Inspect get_queue after submission; never blindly repeat an unknown write."""
        return result(
            BusinessResult[MutationData],
            playback.add_to_queue,
            track_uri,
            device_id,
            dry_run,
        )
