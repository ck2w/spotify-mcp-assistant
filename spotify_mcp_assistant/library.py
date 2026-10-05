"""Saved songs and playlists using current URI-based library endpoints."""
from pydantic import TypeAdapter
from spotify_mcp_assistant import spotify_client as api
from spotify_mcp_assistant.catalog import page,track_detail
from spotify_mcp_assistant.models import TrackURIs,PlaylistURI,PageLimit,Offset
from spotify_mcp_assistant.mutations import mutation,submit_batches


def get_saved_tracks(limit: int = 20, offset: int = 0) -> dict:
    TypeAdapter(PageLimit).validate_python(limit);TypeAdapter(Offset).validate_python(offset)
    data=api.spotify_request('GET','/me/tracks',params={'limit':limit,'offset':offset},required_scopes=('user-library-read',)).json()
    items=[{'added_at':entry.get('added_at'),'track':track_detail(entry['track']) if entry.get('track') else None} for entry in data['items']]
    return page(data,items,limit,offset)


def _save(operation,uris,dry_run,playlist=False):
    if playlist: TypeAdapter(PlaylistURI).validate_python(uris[0])
    else: TypeAdapter(TrackURIs).validate_python(uris)
    data=mutation(operation,{}, {'uris':uris},uris,deduplicate=True)
    if dry_run:return data
    method='DELETE' if operation in ('remove_saved_tracks','unsave_playlist') else 'PUT'
    scopes=('playlist-modify-public',) if playlist else ('user-library-modify',)
    def submit(batch,start):
        api.spotify_request(method,'/me/library',params={'uris':','.join(batch)},required_scopes=scopes)
    return submit_batches(data,40,submit)


def save_tracks(track_uris: list[str], dry_run: bool = True) -> dict:
    return _save('save_tracks',track_uris,dry_run)


def remove_saved_tracks(track_uris: list[str], dry_run: bool = True) -> dict:
    return _save('remove_saved_tracks',track_uris,dry_run)


def save_playlist(playlist_uri: str, dry_run: bool = True) -> dict:
    return _save('save_playlist',[playlist_uri],dry_run,playlist=True)


def unsave_playlist(playlist_uri: str, dry_run: bool = True) -> dict:
    return _save('unsave_playlist',[playlist_uri],dry_run,playlist=True)


def check_saved_tracks(track_uris: list[str]) -> dict:
    TypeAdapter(TrackURIs).validate_python(track_uris)
    result={'items':[],'unqueried_uris':[]}
    for start in range(0,len(track_uris),40):
        batch=track_uris[start:start+40]
        try:
            response=api.spotify_request('GET','/me/library/contains',params={'uris':','.join(batch)},required_scopes=('user-library-read',))
            try: values=response.json()
            except ValueError: values=None
            if not isinstance(values,list) or len(values)!=len(batch) or any(type(value) is not bool for value in values):
                raise api.SpotifyError('spotify_response_error','Invalid saved-state response','Read saved state again later')
        except api.SpotifyError as error:
            result['unqueried_uris']=track_uris[start:]
            error.data=result
            raise
        result['items'].extend({'track_uri':uri,'saved':value} for uri,value in zip(batch,values))
    return result
