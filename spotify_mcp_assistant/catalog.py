"""Music catalog reads and response normalization."""
from urllib.parse import parse_qs, urlsplit
from spotify_mcp_assistant import spotify_client as api


def track_detail(item: dict) -> dict:
    album = item.get('album')
    return {
        'name': item.get('name', ''), 'artists': [a.get('name','') for a in item.get('artists',[])],
        'track_uri': item.get('uri',''), 'url': (item.get('external_urls') or {}).get('spotify',''),
        'duration_ms': item.get('duration_ms'), 'explicit': item.get('explicit'), 'is_playable': item.get('is_playable'),
        'album': {'name':album.get('name'), 'uri':album.get('uri'), 'url':(album.get('external_urls') or {}).get('spotify')} if album else None,
    }


def page(data: dict, items: list, limit: int, offset: int) -> dict:
    next_offset = None
    if data.get('next') and items:
        try:
            candidate = int(parse_qs(urlsplit(data['next']).query)['offset'][0])
            if candidate > offset:
                next_offset = candidate
        except (ValueError, KeyError, TypeError):
            pass
    return {'items':items, 'limit':limit, 'offset':offset, 'total':data.get('total'),
            'has_more': next_offset is not None, 'next_offset':next_offset}


def search_tracks(query: str, limit: int = 5) -> list[dict]:
    if not query.strip() or not 1 <= limit <= 10:
        raise ValueError('Invalid search query or limit')
    data = api.spotify_get('/search', {'q':query.strip(),'type':'track','limit':limit}).json()
    return [{key: track_detail(item)[key] for key in ('name','artists','track_uri','url')}
            for item in data['tracks']['items']]


def get_track(track_uri: str) -> dict:
    from pydantic import TypeAdapter
    from spotify_mcp_assistant.models import TrackURI
    uri = TypeAdapter(TrackURI).validate_python(track_uri)
    return track_detail(api.spotify_get('/tracks/' + uri.rsplit(':',1)[1]).json())
