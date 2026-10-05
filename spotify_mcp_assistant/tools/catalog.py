from typing import Annotated
from pydantic import Field, StringConstraints
from spotify_mcp_assistant import catalog, spotify_client
from spotify_mcp_assistant.models import BusinessResult, TrackDetail, TrackURI, SearchResult
from spotify_mcp_assistant.tools import result


def register_tools(mcp):
    @mcp.tool(annotations={'readOnlyHint':True})
    def search_tracks(query:Annotated[str,StringConstraints(strip_whitespace=True,min_length=1)],
                      limit:Annotated[int,Field(ge=1,le=10)]=5)->SearchResult:
        """Search tracks; ask the user to choose when versions are ambiguous. Use track_uri, not a title, in writes."""
        return result(SearchResult,spotify_client.search_tracks,query,limit)

    @mcp.tool(annotations={'readOnlyHint':True})
    def get_track(track_uri:TrackURI)->BusinessResult[TrackDetail]:
        """Read details for a Spotify track URI returned by search_tracks."""
        return result(BusinessResult[TrackDetail],catalog.get_track,track_uri)
