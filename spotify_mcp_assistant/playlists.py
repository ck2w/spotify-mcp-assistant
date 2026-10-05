"""Playlist reads; item positions include unavailable and non-track entries."""
from pydantic import TypeAdapter
from spotify_mcp_assistant import spotify_client as api
from spotify_mcp_assistant.catalog import page, track_detail
from spotify_mcp_assistant.models import PlaylistID, PageLimit, Offset

READ_SCOPES = ('playlist-read-private', 'playlist-read-collaborative')
WRITE_SCOPES = ('playlist-modify-private', 'playlist-modify-public')


def playlist_summary(data: dict) -> dict:
    contents = data.get('items', data.get('tracks'))
    return {'playlist_id':data['id'], 'playlist_uri':data.get('uri','spotify:playlist:'+data['id']),
        'name':data.get('name',''), 'url':(data.get('external_urls') or {}).get('spotify',''),
        'owner_id':(data.get('owner') or {}).get('id'), 'public':data.get('public'),
        'collaborative':data.get('collaborative'), 'snapshot_id':data.get('snapshot_id'),
        'total':contents.get('total') if isinstance(contents,dict) else None,
        'contents_accessible':isinstance(contents,dict)}


def list_playlists(limit: int = 20, offset: int = 0) -> dict:
    TypeAdapter(PageLimit).validate_python(limit); TypeAdapter(Offset).validate_python(offset)
    data = api.spotify_request('GET','/me/playlists',params={'limit':limit,'offset':offset},required_scopes=READ_SCOPES).json()
    return page(data,[playlist_summary(item) for item in data['items']],limit,offset)


def get_playlist(playlist_id: str) -> dict:
    TypeAdapter(PlaylistID).validate_python(playlist_id)
    data = api.spotify_request('GET','/playlists/'+playlist_id,required_scopes=READ_SCOPES).json()
    return playlist_summary(data)


def get_playlist_tracks(playlist_id: str, limit: int = 20, offset: int = 0) -> dict:
    TypeAdapter(PlaylistID).validate_python(playlist_id)
    TypeAdapter(PageLimit).validate_python(limit); TypeAdapter(Offset).validate_python(offset)
    data = api.spotify_request('GET',f'/playlists/{playlist_id}/items',params={'limit':limit,'offset':offset},required_scopes=READ_SCOPES).json()
    if 'items' not in data:
        raise api.SpotifyError('contents_unavailable','Playlist contents are not accessible','Select a playlist you own or collaborate on')
    entries=[]
    for index, entry in enumerate(data['items']):
        entry = entry or {}
        item=entry.get('item',entry.get('track'))
        kind = item.get('type','unknown') if item else 'unavailable'
        entries.append({'position':offset+index,'added_at':entry.get('added_at'),
            'is_local':bool(entry.get('is_local') or (item or {}).get('is_local')), 'item_type':kind,
            'track':track_detail(item) if kind=='track' else None})
    return page(data,entries,limit,offset)
