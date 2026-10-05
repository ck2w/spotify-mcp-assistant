from typing import Annotated

from pydantic import Field, StringConstraints

from spotify_mcp_assistant import playlists
from spotify_mcp_assistant.models import (
    BusinessResult,
    MutationData,
    Offset,
    Page,
    PageLimit,
    PlaylistEntry,
    PlaylistID,
    PlaylistSummary,
    ReplacementURIs,
    TrackURIs,
)
from spotify_mcp_assistant.tools import result


def register_tools(mcp):
    @mcp.tool(annotations={"readOnlyHint": True})
    def list_playlists(
        limit: PageLimit = 20, offset: Offset = 0
    ) -> BusinessResult[Page[PlaylistSummary]]:
        """Read one page of your playlists. Use next_offset to request the next page; never assume this page is the whole library."""
        return result(
            BusinessResult[Page[PlaylistSummary]],
            playlists.list_playlists,
            limit,
            offset,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    def get_playlist(playlist_id: PlaylistID) -> BusinessResult[PlaylistSummary]:
        """Read playlist metadata and snapshot_id. playlist_id is a bare ID, not a URI. Inaccessible content is not an empty playlist."""
        return result(
            BusinessResult[PlaylistSummary], playlists.get_playlist, playlist_id
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    def get_playlist_tracks(
        playlist_id: PlaylistID, limit: PageLimit = 20, offset: Offset = 0
    ) -> BusinessResult[Page[PlaylistEntry]]:
        """Read one page of playlist items, preserving all positions including unavailable/local/non-track items. Use next_offset until absent to verify full contents."""
        return result(
            BusinessResult[Page[PlaylistEntry]],
            playlists.get_playlist_tracks,
            playlist_id,
            limit,
            offset,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def create_playlist(
        name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)],
        description: str = "",
        public: bool = False,
        collaborative: bool = False,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Create an empty playlist (private by default). Preview first, wait for new user confirmation, then execute identical parameters. Use the returned real playlist_id to add tracks; preview has no ID."""
        return result(
            BusinessResult[MutationData],
            playlists.create_playlist,
            name,
            description,
            public,
            collaborative,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def update_playlist_details(
        playlist_id: PlaylistID,
        name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
        | None = None,
        description: str | None = None,
        public: bool | None = None,
        collaborative: bool | None = None,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Preview playlist metadata updates, wait for new user confirmation, then execute. Null leaves a field unchanged; empty description clears it."""
        return result(
            BusinessResult[MutationData],
            playlists.update_playlist_details,
            playlist_id,
            name,
            description,
            public,
            collaborative,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def add_playlist_tracks(
        playlist_id: PlaylistID,
        track_uris: TrackURIs,
        position: Offset | None = None,
        expected_snapshot_id: str | None = None,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Preview adding tracks (1–500); preserves input order and duplicates. Confirm before executing. Pass preview snapshot as expected_snapshot_id. Batches are non-atomic; read state on partial or unknown before retrying."""
        return result(
            BusinessResult[MutationData],
            playlists.add_playlist_tracks,
            playlist_id,
            track_uris,
            position,
            expected_snapshot_id,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def remove_playlist_tracks(
        playlist_id: PlaylistID,
        track_uris: TrackURIs,
        expected_snapshot_id: str | None = None,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Preview removing tracks by URI, including repeated occurrences, not a selected occurrence by position. Confirm before execution; pass preview snapshot. Inspect progress and read state on failure."""
        return result(
            BusinessResult[MutationData],
            playlists.remove_playlist_tracks,
            playlist_id,
            track_uris,
            expected_snapshot_id,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def replace_playlist_tracks(
        playlist_id: PlaylistID,
        track_uris: ReplacementURIs,
        expected_snapshot_id: str | None = None,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Preview replacing ALL playlist contents (maximum 100 tracks); an empty list CLEARS it. Wait for new user confirmation; pass preview snapshot. Never silently split an oversized replacement."""
        return result(
            BusinessResult[MutationData],
            playlists.replace_playlist_tracks,
            playlist_id,
            track_uris,
            expected_snapshot_id,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def reorder_playlist_tracks(
        playlist_id: PlaylistID,
        range_start: Offset,
        insert_before: Offset,
        range_length: Annotated[int, Field(ge=1)] = 1,
        expected_snapshot_id: str | None = None,
        dry_run: bool = True,
    ) -> BusinessResult[MutationData]:
        """Preview moving a continuous range; positions are zero-based and include unavailable/non-track items. insert_before is the original index before removal. Confirm first and pass preview snapshot. Read contents to verify."""
        return result(
            BusinessResult[MutationData],
            playlists.reorder_playlist_tracks,
            playlist_id,
            range_start,
            insert_before,
            range_length,
            expected_snapshot_id,
            dry_run,
        )
