import httpx


def test_track_detail_without_removed_fields(fake_http, fake_track):
    from spotify_mcp_assistant import catalog
    fake_http.enqueue(httpx.Response(200, json=fake_track))
    result = catalog.get_track('spotify:track:' + 'a'*22)
    assert result['name'] == 'Test Song'
    assert result['duration_ms'] is None
    assert result['is_playable'] is None
    assert fake_http.calls[0]['path'] == '/tracks/' + 'a'*22
