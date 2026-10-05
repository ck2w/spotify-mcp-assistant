import asyncio
import httpx
import pytest
from fastmcp import Client


def test_page_preserves_non_track_positions(fake_http, fake_track):
    from spotify_mcp_assistant import playlists
    fake_http.enqueue_playlist_items([None, {'type': 'episode'}, fake_track])
    result = playlists.get_playlist_tracks('p'*22)
    assert [entry['position'] for entry in result['items']] == [0,1,2]
    assert result['items'][0]['track'] is None
    assert result['items'][1]['item_type'] == 'episode'
    assert result['items'][2]['track']['name'] == 'Test Song'
    assert result['next_offset'] is None


@pytest.mark.parametrize('field', ['track', 'item'])
def test_playlist_content_field_variants(fake_http, fake_track, field):
    from spotify_mcp_assistant import playlists
    fake_http.enqueue(httpx.Response(200, json={'items': [{field:fake_track}], 'next':'https://api.spotify.com/v1/playlists/x/items?offset=21&limit=20', 'total':30}))
    result = playlists.get_playlist_tracks('p'*22, offset=20)
    assert result['items'][0]['position'] == 20
    assert result['next_offset'] == 21


def test_missing_content_is_not_empty_playlist(fake_http):
    from spotify_mcp_assistant import playlists
    fake_http.enqueue_playlist_precheck()
    assert playlists.get_playlist('p'*22)['contents_accessible'] is True
    fake_http.enqueue(httpx.Response(200, json={'id':'p'*22,'name':'Other','uri':'spotify:playlist:'+'p'*22}))
    assert playlists.get_playlist('p'*22)['contents_accessible'] is False


@pytest.mark.parametrize('args', [{'limit':0}, {'limit':51}, {'offset':-1}])
def test_playlist_page_schema_rejects_bad_bounds(args):
    from spotify_mcp_assistant.server import mcp
    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool('list_playlists', args, raise_on_error=False)
            assert result.is_error
    asyncio.run(run())
