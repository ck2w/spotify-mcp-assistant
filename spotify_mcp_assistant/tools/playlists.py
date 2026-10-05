from spotify_mcp_assistant import playlists
from spotify_mcp_assistant.models import BusinessResult, Page, PlaylistSummary, PlaylistEntry, PlaylistID, PageLimit, Offset
from spotify_mcp_assistant.tools import result


def register_tools(mcp):
    @mcp.tool(annotations={'readOnlyHint':True})
    def list_playlists(limit:PageLimit=20,offset:Offset=0)->BusinessResult[Page[PlaylistSummary]]:
        """Read one page of your playlists. Use next_offset to request the next page; never assume this page is the whole library."""
        return result(BusinessResult[Page[PlaylistSummary]],playlists.list_playlists,limit,offset)

    @mcp.tool(annotations={'readOnlyHint':True})
    def get_playlist(playlist_id:PlaylistID)->BusinessResult[PlaylistSummary]:
        """Read playlist metadata and snapshot_id. playlist_id is a bare ID, not a URI. Inaccessible content is not an empty playlist."""
        return result(BusinessResult[PlaylistSummary],playlists.get_playlist,playlist_id)

    @mcp.tool(annotations={'readOnlyHint':True})
    def get_playlist_tracks(playlist_id:PlaylistID,limit:PageLimit=20,offset:Offset=0)->BusinessResult[Page[PlaylistEntry]]:
        """Read one page of playlist items, preserving all positions including unavailable/local/non-track items. Use next_offset until absent to verify full contents."""
        return result(BusinessResult[Page[PlaylistEntry]],playlists.get_playlist_tracks,playlist_id,limit,offset)
