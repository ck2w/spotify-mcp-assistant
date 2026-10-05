from spotify_mcp_assistant import library
from spotify_mcp_assistant.models import (
    BusinessResult,
    MutationData,
    Offset,
    Page,
    PageLimit,
    PlaylistURI,
    SavedCheckData,
    SavedTrack,
    TrackURIs,
)
from spotify_mcp_assistant.tools import result


def register_tools(mcp):
    @mcp.tool(annotations={"readOnlyHint": True})
    def get_saved_tracks(
        limit: PageLimit = 20, offset: Offset = 0
    ) -> BusinessResult[Page[SavedTrack]]:
        """Read one page of saved songs and added_at. Continue with next_offset if present."""
        return result(
            BusinessResult[Page[SavedTrack]], library.get_saved_tracks, limit, offset
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    def check_saved_tracks(track_uris: TrackURIs) -> BusinessResult[SavedCheckData]:
        """Check saved state for 1–500 track URIs in input order. On failure known results remain; unqueried songs are unknown, not false."""
        return result(
            BusinessResult[SavedCheckData], library.check_saved_tracks, track_uris
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def save_tracks(
        track_uris: TrackURIs, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview saving songs, then wait for a new user confirmation before executing the same parameters. Writes use batches of 40 and are non-atomic; verify with check_saved_tracks."""
        return result(
            BusinessResult[MutationData], library.save_tracks, track_uris, dry_run
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def remove_saved_tracks(
        track_uris: TrackURIs, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview removing songs from favorites; wait for new user confirmation. Partial/unknown writes need state inspection before retry. Verify with check_saved_tracks."""
        return result(
            BusinessResult[MutationData],
            library.remove_saved_tracks,
            track_uris,
            dry_run,
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def save_playlist(
        playlist_uri: PlaylistURI, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview saving a playlist to your library; this does not copy its contents. Confirm in a new user message before executing; verify with list_playlists."""
        return result(
            BusinessResult[MutationData], library.save_playlist, playlist_uri, dry_run
        )

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }
    )
    def unsave_playlist(
        playlist_uri: PlaylistURI, dry_run: bool = True
    ) -> BusinessResult[MutationData]:
        """Preview removing a playlist from your library; this does NOT delete the playlist. Wait for new user confirmation before executing."""
        return result(
            BusinessResult[MutationData], library.unsave_playlist, playlist_uri, dry_run
        )
